import unittest
import responses
import requests
import json
from unittest.mock import Mock
from jfintegrity import jfintegrity

stats_body = '''
{
    "repo": "myrepo",
    "path": "/mysubdir/myartifact.zip",
    "created": "2022-07-06T14:54:00.388Z",
    "createdBy": "someuser",
    "lastModified": "2023-02-01T02:37:39.794Z",
    "modifiedBy": "someuser",
    "lastUpdated": "2023-02-01T02:37:43.518Z",
    "downloadUri": "https://myserver/artifactory/myrepo/mysubdir/myartifact.zip",
    "mimeType": "application/zip",
    "size": "126419978",
    "checksums": {
        "sha1": "5029c57c403e5af0f4b22f387a37d171df655908",
        "md5": "5cdd80c561fa89d345f23e2ef0bb7624",
        "sha256": "7d7bae2d0557f174aa033ba4dbd0f7be356138145910a7817ee4d380429b3c9f"
    },
    "originalChecksums": {
        "sha1": "5029c57c403e5af0f4b22f387a37d171df655908",
        "md5": "5cdd80c561fa89d345f23e2ef0bb7624",
        "sha256": "7d7bae2d0557f174aa033ba4dbd0f7be356138145910a7817ee4d380429b3c9f"
    },
    "uri": "https://myserver/artifactory/api/storage/myrepo/mysubdir/myartifact.zip"
}
'''
stats_body_failed = '''
{
    "errors": [
        {
            "status": 404,
            "message": "Unable to find item"
        }
    ]
}
'''
trace_body = '''
Request ID: 2e280515
Repo Path ID: myrepo/mysubdir/myartifact.zip
Method Name: GET
User: someuser
Time: 2023-02-02T00:54:57.734Z
Thread: http-nio-8081-exec-71
Steps: 
2023-02-02T00:54:57.734Z Received request
2023-02-02T00:54:57.734Z Request source = 1.2.3.4, Last modified = 31-12-69 23:59:59 +00:00, If modified since = -1, Thread name = http-nio-8081-exec-71
2023-02-02T00:54:57.734Z Executing any BeforeDownloadRequest user plugins that may exist
2023-02-02T00:54:57.734Z Retrieving info from local repository 'myrepo' type Generic
2023-02-02T00:54:57.741Z Requested resource is found = true
2023-02-02T00:54:57.741Z Requested resource is blocked = false
2023-02-02T00:54:57.741Z Request is HEAD = false
2023-02-02T00:54:57.741Z Request is for a checksum = false
2023-02-02T00:54:57.741Z Target repository is not remote or doesn't store locally = true
2023-02-02T00:54:57.741Z Requested resource was not modified = false
2023-02-02T00:54:57.741Z Responding with found resource
2023-02-02T00:54:57.741Z Executing any AltAllResponses user plugins that may exist
2023-02-02T00:54:57.741Z Alternative response status is set to 0 and message to 'null'
2023-02-02T00:54:57.741Z Found no alternative content handles
2023-02-02T00:54:57.741Z Executing any AltResponse user plugins that may exist
2023-02-02T00:54:57.741Z Alternative response status is set to -1 and message to 'null'
2023-02-02T00:54:57.741Z Found no alternative content handles
2023-02-02T00:54:57.741Z Retrieving a content handle from target repo
2023-02-02T00:54:57.741Z The requested resource isn't pre-resolved
2023-02-02T00:54:57.741Z Target repository isn't virtual - verifying that downloading is allowed
2023-02-02T00:54:57.741Z Creating a resource handle from 'myrepo/mysubdir/myartifact.zip'
2023-02-02T00:54:57.743Z Identified requested resource as a file
2023-02-02T00:54:57.743Z Requested resource is an ordinary artifact - using normal content handle with length '71251'
2023-02-02T00:54:57.760Z Executing any BeforeDownload user plugins that may exist
2023-02-02T00:54:57.760Z Responding with selected content handle
2023-02-02T00:54:57.764Z Request succeeded
'''
trace_body_unsafe = '''
Request ID: 2e280515
Repo Path ID: myrepo/my sub dir/my artifact.zip
Method Name: GET
User: someuser
Time: 2023-02-02T00:54:57.734Z
Thread: http-nio-8081-exec-71
Steps: 
2023-02-02T00:54:57.734Z Received request
2023-02-02T00:54:57.734Z Request source = 1.2.3.4, Last modified = 31-12-69 23:59:59 +00:00, If modified since = -1, Thread name = http-nio-8081-exec-71
2023-02-02T00:54:57.734Z Executing any BeforeDownloadRequest user plugins that may exist
2023-02-02T00:54:57.734Z Retrieving info from local repository 'myrepo' type Generic
2023-02-02T00:54:57.741Z Requested resource is found = true
2023-02-02T00:54:57.741Z Requested resource is blocked = false
2023-02-02T00:54:57.741Z Request is HEAD = false
2023-02-02T00:54:57.741Z Request is for a checksum = false
2023-02-02T00:54:57.741Z Target repository is not remote or doesn't store locally = true
2023-02-02T00:54:57.741Z Requested resource was not modified = false
2023-02-02T00:54:57.741Z Responding with found resource
2023-02-02T00:54:57.741Z Executing any AltAllResponses user plugins that may exist
2023-02-02T00:54:57.741Z Alternative response status is set to 0 and message to 'null'
2023-02-02T00:54:57.741Z Found no alternative content handles
2023-02-02T00:54:57.741Z Executing any AltResponse user plugins that may exist
2023-02-02T00:54:57.741Z Alternative response status is set to -1 and message to 'null'
2023-02-02T00:54:57.741Z Found no alternative content handles
2023-02-02T00:54:57.741Z Retrieving a content handle from target repo
2023-02-02T00:54:57.741Z The requested resource isn't pre-resolved
2023-02-02T00:54:57.741Z Target repository isn't virtual - verifying that downloading is allowed
2023-02-02T00:54:57.741Z Creating a resource handle from 'myrepo/my sub dir/my artifact.zip'
2023-02-02T00:54:57.743Z Identified requested resource as a file
2023-02-02T00:54:57.743Z Requested resource is an ordinary artifact - using normal content handle with length '71251'
2023-02-02T00:54:57.760Z Executing any BeforeDownload user plugins that may exist
2023-02-02T00:54:57.760Z Responding with selected content handle
2023-02-02T00:54:57.764Z Request succeeded

'''
trace_body_failed = '''
Request ID: 9fffb38b
Repo Path ID: myrepo/mysubdir/myartifact.zip
Method Name: GET
User: someuser
Time: 2023-02-04T01:18:30.478Z
Thread: http-nio-8081-exec-20
Steps: 
2023-02-04T01:18:30.478Z Received request
2023-02-04T01:18:30.478Z Request source = 1.2.3.4, Last modified = 31-12-69 23:59:59 +00:00, If modified since = -1, Thread name = http-nio-8081-exec-20
2023-02-04T01:18:30.478Z Executing any BeforeDownloadRequest user plugins that may exist
2023-02-04T01:18:30.478Z Retrieving info from local repository 'myrepo' type Generic
2023-02-04T01:18:30.481Z Unable to find resource in myrepo/mysubdir/myartifact.zip
2023-02-04T01:18:30.481Z Requested resource is found = false
2023-02-04T01:18:30.481Z Requested resource is blocked = false
2023-02-04T01:18:30.481Z Request is HEAD = false
2023-02-04T01:18:30.481Z Request is for a checksum = false
2023-02-04T01:18:30.481Z Target repository is not remote or doesn't store locally = true
2023-02-04T01:18:30.481Z Requested resource was not modified = false
2023-02-04T01:18:30.481Z Responding with unfound resource
2023-02-04T01:18:30.481Z Setting default response status to '404' reason to 'Resource not found'
2023-02-04T01:18:30.481Z Response is an instance of UnfoundRepoResourceReason
2023-02-04T01:18:30.481Z Configured to hide un-authorized resources = false
2023-02-04T01:18:30.481Z Configured to hide real status of un-authorized resources = false for repo myrepo
2023-02-04T01:18:30.481Z Original response status is auth related = false
2023-02-04T01:18:30.481Z Using original response status of '404' and message 'File not found.'
2023-02-04T01:18:30.481Z Sending error with status 404 and message 'File not found.'
2023-02-04T01:18:30.481Z Executing any AfterDownloadErrorAction user plugins that may exist
2023-02-04T01:18:30.481Z Response code wasn't modified by the user plugins
2023-02-04T01:18:30.481Z Sending response with the status '404' and the message 'File not found.'
'''
get_contents = '''
{
    "uri": "https://myserver/artifactory/api/storage/myrepo",
    "created": "2023-02-02T01:38:05.225Z",
    "files": [
        {
            "uri": "/",
            "size": -1,
            "lastModified": "2021-12-07T18:36:08.594Z",
            "folder": true
        },
        {
            "uri": "/mysubdir/art1.zip",
            "size": 192000,
            "lastModified": "2023-01-10T17:00:00.235Z",
            "folder": false,
            "sha1": "15b4e89cf7ccc6c42569ce0592a8e0847455bd21",
            "sha2": "64ccb1f7564bf678ba0f6c93c46b188f70fb5ea49064b23d74259a47fef45c08",
            "mdTimestamps": {
                "properties": "2021-12-10T17:00:00.409Z"
            }
        },
        {
            "uri": "/mysubdir/art2.zip",
            "size": 325,
            "lastModified": "2021-12-10T17:00:00.472Z",
            "folder": false,
            "sha1": "8a4a94d69e43c06c20cda713fbe51277abed46c8",
            "sha2": "020db870ea9439f2c8535be0fcb34b5c3096e870d6841fa6c51a9890302f78c2",
            "mdTimestamps": {
                "properties": "2021-12-10T17:00:00.610Z"
            }
        },
        {
            "uri": "/mysubdir/art3.zip",
            "size": 1934,
            "lastModified": "2023-02-10T17:00:00.666Z",
            "folder": false,
            "sha1": "98b0a25eca2ce68b491dd751ed7265c6243b835b",
            "sha2": "ac577492d275c5c5454fb1ef598e9fb33b7677cad4bfc7ce0d17fcd3b76f209c",
            "mdTimestamps": {
                "properties": "2021-12-10T17:00:00.783Z"
            }
        }
    ]
}
'''
get_contents2 = '''
{
    "uri": "https://myserver/artifactory/api/storage/myrepo2",
    "created": "2023-02-02T01:38:05.225Z",
    "files": [
        {
            "uri": "/",
            "size": -1,
            "lastModified": "2021-12-07T18:36:08.594Z",
            "folder": true
        },
        {
            "uri": "/mysubdir/art1.zip",
            "size": 192000,
            "lastModified": "2023-01-10T17:00:00.235Z",
            "folder": false,
            "sha1": "15b4e89cf7ccc6c42569ce0592a8e0847455bd21",
            "sha2": "64ccb1f7564bf678ba0f6c93c46b188f70fb5ea49064b23d74259a47fef45c08",
            "mdTimestamps": {
                "properties": "2021-12-10T17:00:00.409Z"
            }
        },
        {
            "uri": "/mysubdir/art4.zip",
            "size": 325,
            "lastModified": "2021-12-10T17:00:00.472Z",
            "folder": false,
            "sha1": "8a4a94d69e43c06c20cda713fbe51277abed46c8",
            "sha2": "020db870ea9439f2c8535be0fcb34b5c3096e870d6841fa6c51a9890302f78c2",
            "mdTimestamps": {
                "properties": "2021-12-10T17:00:00.610Z"
            }
        },
        {
            "uri": "/mysubdir/art5.zip",
            "size": 1934,
            "lastModified": "2023-01-10T17:00:00.666Z",
            "folder": false,
            "sha1": "98b0a25eca2ce68b491dd751ed7265c6243b835b",
            "sha2": "ac577492d275c5c5454fb1ef598e9fb33b7677cad4bfc7ce0d17fcd3b76f209c",
            "mdTimestamps": {
                "properties": "2021-12-10T17:00:00.783Z"
            }
        }
    ]
}
'''
get_contents3 = '''
{
    "uri": "https://myserver/artifactory/api/storage/myrepo3",
    "created": "2023-02-02T01:38:05.225Z",
    "files": [
        {
            "uri": "/",
            "size": -1,
            "lastModified": "2021-12-07T18:36:08.594Z",
            "folder": true
        },
        {
            "uri": "/mysubdir/art6.zip",
            "size": 192000,
            "lastModified": "2021-12-10T17:00:00.235Z",
            "folder": false,
            "sha1": "15b4e89cf7ccc6c42569ce0592a8e0847455bd21",
            "sha2": "64ccb1f7564bf678ba0f6c93c46b188f70fb5ea49064b23d74259a47fef45c08",
            "mdTimestamps": {
                "properties": "2021-12-10T17:00:00.409Z"
            }
        },
        {
            "uri": "/mysubdir/art7.zip",
            "size": 325,
            "lastModified": "2023-01-10T17:00:00.472Z",
            "folder": false,
            "sha1": "8a4a94d69e43c06c20cda713fbe51277abed46c8",
            "sha2": "020db870ea9439f2c8535be0fcb34b5c3096e870d6841fa6c51a9890302f78c2",
            "mdTimestamps": {
                "properties": "2021-12-10T17:00:00.610Z"
            }
        },
        {
            "uri": "/mysubdir/art8.zip",
            "size": 1934,
            "lastModified": "2021-12-10T17:00:00.666Z",
            "folder": false,
            "sha1": "98b0a25eca2ce68b491dd751ed7265c6243b835b",
            "sha2": "ac577492d275c5c5454fb1ef598e9fb33b7677cad4bfc7ce0d17fcd3b76f209c",
            "mdTimestamps": {
                "properties": "2021-12-10T17:00:00.783Z"
            }
        }
    ]
}
'''
stats_body_is_folder = '''
{
    "repo": "myrepo",
    "path": "/mysubdir",
    "created": "2022-07-06T14:53:59.586Z",
    "createdBy": "someuser",
    "lastModified": "2022-07-06T14:53:59.586Z",
    "modifiedBy": "someuser",
    "lastUpdated": "2022-07-06T14:53:59.586Z",
    "children": [
        {
            "uri": "/myartifact1",
            "folder": false
        },
        {
            "uri": "/myartifact2",
            "folder": false
        },
        {
            "uri": "/myartifact3",
            "folder": false
        }
    ],
    "uri": "https://myserver/artifactory/api/storage/myrepo/mysubdir"
}
'''
class TestjfIntegrity(unittest.TestCase):

    def setUp(self):
        self.jfi = jfintegrity.jfIntegrity(server='https://myserver', access_token='myaccesstoken')

    @responses.activate
    def test_test_connection_success(self):
        responses.add(responses.GET, 'https://myserver', status=200)
        ret = self.jfi.test_connection()
        assert ret == True

    @responses.activate
    def test_test_connection_failed(self):
        responses.add(responses.GET, 'https://myserver', body=requests.ConnectionError())
        ret = self.jfi.test_connection()
        assert ret == False

    @responses.activate
    def test_get_stats_ok(self):
        responses.add(responses.GET, 'https://myserver/artifactory/api/storage/myrepo/mysubdir/myartifact.zip', body=stats_body, status=200)
        ret = self.jfi.get_stats('myrepo/mysubdir/myartifact.zip')
        assert ret == json.loads(stats_body)

    @responses.activate
    def test_get_stats_non_ok(self):
        responses.add(responses.GET, 'https://myserver/artifactory/api/storage/myrepo/mysubdir/myartifact.zip', body=stats_body_failed, status=404)
        ret = self.jfi.get_stats('myrepo/mysubdir/myartifact.zip')
        assert ret == None

    @responses.activate
    def test_get_stats_request_exception(self):
        responses.add(responses.GET, 'https://myserver/artifactory/api/storage/myrepo/mysubdir/myartifact.zip')
        with self.assertRaises(requests.RequestException) as context:
            ret = self.jfi.get_stats('myrepo/mysubdir/myartifact.zip')
            self.assertTrue('unrecoverable exception' in context.exception)

    @responses.activate
    def test_get_trace_ok(self):
        responses.add(responses.GET, 'https://myserver/artifactory/myrepo/mysubdir/myartifact.zip?skipUpdateStats=true&trace=null', body=trace_body, status=200)
        ret = self.jfi.get_trace('myrepo/mysubdir/myartifact.zip')
        assert ret == trace_body

    @responses.activate
    def test_get_trace_url_has_spaces(self):
        responses.add(responses.GET, 'https://myserver/artifactory/myrepo/my%20sub%20dir/my%20artifact.zip?skipUpdateStats=true&trace=null', body=trace_body_unsafe, status=200)
        ret = self.jfi.get_trace('myrepo/my sub dir/my artifact.zip')
        assert ret == trace_body_unsafe

    @responses.activate
    def test_get_contents_ok(self):
        responses.add(responses.GET, 'https://myserver/artifactory/api/storage/myrepo?list=null&deep=1&listFolders=0&mdTimestamps=1&includeRootPath=1', body=get_contents, status=200)
        ret = self.jfi.get_contents('myrepo')
        assert ret == json.loads(get_contents)

    @responses.activate
    def test_del_artifact_ok(self):
        responses.add(responses.DELETE, 'https://myserver/artifactory/myrepo/mysubdir/myartifact.zip', status=204)
        self.jfi.is_folder = Mock(return_value=False)
        ret = self.jfi.del_artifact('myrepo/mysubdir/myartifact.zip')
        assert responses.assert_call_count('https://myserver/artifactory/myrepo/mysubdir/myartifact.zip', 1) is True

    @responses.activate
    def test_del_artifact_is_folder_does_not_delete(self):
        responses.add(responses.DELETE, 'https://myserver/artifactory/myrepo/mysubdir', status=204)
        self.jfi.is_folder = Mock(return_value=True)
        ret = self.jfi.del_artifact('myrepo/mysubdir')
        assert responses.assert_call_count('https://myserver/artifactory/myrepo/mysubdir', 0) is True

    def test_trace_ok(self):
        jfintegrity.output = []
        self.jfi.get_trace = Mock(return_value=trace_body)
        ret = self.jfi.trace('myrepo/mysubdir/myartifact.zip')
        assert jfintegrity.output == [('myrepo/mysubdir/myartifact.zip', 'artifact_traceable')]

    def test_trace_notthere(self):
        jfintegrity.output = []
        self.jfi.get_trace = Mock(return_value=trace_body_failed, status=404)
        ret = self.jfi.trace('myrepo/mysubdir/myartifact.zip')
        assert jfintegrity.output == [('myrepo/mysubdir/myartifact.zip', 'artifact_untraceable')]

    def test_is_folder_true(self):
        self.jfi.get_stats = Mock(return_value=json.loads(stats_body_is_folder))
        ret = self.jfi.is_folder('myrepo/mysubdir')
        assert ret == True

    def test_is_folder_false(self):
        self.jfi.get_stats = Mock(return_value=json.loads(stats_body))
        ret = self.jfi.is_folder('myrepo/mysubdir/myartifact.zip')
        assert ret == False

    def test_is_folder_error_returns_true(self):
        self.jfi.get_stats = Mock(return_value=json.loads(stats_body_failed))
        ret = self.jfi.is_folder('myrepo/mysubdir/myartifact.zip.notathing')
        assert ret == True

    def test_read_items_returns_correct_list(self):
        ret = self.jfi.read_items('tests/rfile')
        assert ret == ['myrepo1', 'myrepo2', 'myrepo3']

    def test_read_items_nofile_exits_with_error(self):
        with self.assertRaises(SystemExit):
            ret = self.jfi.read_items('afilenotthere')

    def side_effect_get_contents_multiple_calls(self, repository, after=None):
        if repository == 'myrepo1':
            return json.loads(get_contents)
        elif repository == 'myrepo2':
            return json.loads(get_contents2)
        else:
            return json.loads(get_contents3)

    def test_cat_artifacts_returns_list_of_items(self):
        self.jfi.get_contents = Mock(side_effect=self.side_effect_get_contents_multiple_calls)
        repos = ['myrepo1', 'myrepo2', 'myrepo3']
        ret = self.jfi.cat_artifacts(repos, None)
        expected = ['myrepo1/mysubdir/art1.zip', 'myrepo1/mysubdir/art2.zip', 'myrepo1/mysubdir/art3.zip', 
                    'myrepo2/mysubdir/art1.zip', 'myrepo2/mysubdir/art4.zip', 'myrepo2/mysubdir/art5.zip', 
                    'myrepo3/mysubdir/art6.zip', 'myrepo3/mysubdir/art7.zip', 'myrepo3/mysubdir/art8.zip']
        self.assertEqual(ret, expected)

    def test_cat_artifacts_with_after_returns_expected_items(self):
        self.jfi.get_contents = Mock(side_effect=self.side_effect_get_contents_multiple_calls)
        repos = ['myrepo1', 'myrepo2', 'myrepo3']
        ret = self.jfi.cat_artifacts(repos, '2023-01-01')
        expected = ['myrepo1/mysubdir/art1.zip', 'myrepo1/mysubdir/art3.zip', 'myrepo2/mysubdir/art1.zip',
                     'myrepo2/mysubdir/art5.zip', 'myrepo3/mysubdir/art7.zip']
        self.assertEqual(ret, expected)

    def side_effect_read_items_multiple_calls(self, file):
        if file == 'afile':
            return ['myrepo1/mysubdir/art1.zip', 'myrepo1/mysubdir/art3.zip', 'myrepo2/mysubdir/art1.zip']
        elif file == 'rfile':
            return ['myrepo1', 'myrepo2']

    def side_effect_cat_artifacts_multiple_calls(self, repos, after=None):
        if repos == ['myrepo1']:
            return ['myrepo1/mysubdir/art1.zip', 'myrepo1/mysubdir/art2.zip', 'myrepo1/mysubdir/art3.zip']
        if repos == ['myrepo1', 'myrepo2']:
            return ['myrepo1/mysubdir/art1.zip', 'myrepo1/mysubdir/art2.zip', 'myrepo1/mysubdir/art3.zip', 
                    'myrepo2/mysubdir/art1.zip', 'myrepo2/mysubdir/art4.zip', 'myrepo2/mysubdir/art5.zip']

    def test_compile_artifacts_returns_list_of_items(self):
        self.jfi.cat_artifacts = Mock(side_effect=self.side_effect_cat_artifacts_multiple_calls)
        self.jfi.read_items = Mock(side_effect=self.side_effect_read_items_multiple_calls)
        ret = self.jfi.compile_artifacts(repos=['myrepo1'], afile='afile', rfile='rfile')
        expected = ['myrepo2/mysubdir/art5.zip', 'myrepo2/mysubdir/art4.zip', 'myrepo1/mysubdir/art2.zip',
                    'myrepo2/mysubdir/art1.zip', 'myrepo1/mysubdir/art1.zip', 'myrepo1/mysubdir/art3.zip']
        self.assertEqual(ret.sort(), expected.sort())
