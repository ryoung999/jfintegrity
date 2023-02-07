"""Jfrog artifact integrity checker.

Usage: 
    jfintegrity.py check [-hvVt THREADS] [--access-token=ACCESS_TOKEN] [--after AFTER_DATE]
                         [--afile=ART_FILE] [--rfile=REPO_FILE] [--url=URL] [REPO]...
    jfintegrity.py delete [-hvVt THREADS] [--access-token=ACCESS_TOKEN]
                          [--url=URL] DEL_FILE

Options:
    -h                            Show this screen
    -v                            Show version
    -V                            Verbose output
    -t THREADS --threads=THREADS  specify number of threads [default: 10]
    --url=URL                     specify the base url of the artifactory instance
    --access-token=ACCESS_TOKEN   provide access token
    --afile=ART_FILE              provide artifact file, one artifact path per line
    --rfile=REPO_FILE             provide repository file, one repository per line
    --after=AFTER_DATE            operate only on artifacts last modified after AFTER_DATE (ignores afile artifacts) ex: 2023-01-01
    DEL_FILE                      provide file of artifacts to delete, one artifact path per line
"""
import requests
import logging
import threading
from queue import Empty, Queue
from docopt import docopt
from urllib import parse
from os.path import isfile
from .helpers import get_config
from datetime import datetime
from sys import exit

TRACE_SUCCESS = "Request succeeded"
ARTIFACT_GOOD = 'artifact_traceable'
ARTIFACT_BAD = 'artifact_untraceable'
ARTIFACT_UNKNOWN = 'trace_failure'
ARTIFACT_DELETED = 'artifact_deleted'
ARTIFACT_NOT_DELETED = 'artifact_not_deleted'
ARTIFACT_IS_FOLDER = 'artifact_is_folder'
output = []
after_date = ''

class jfIntegrity():
    """A class to provide Jfrog artifact integrity checking capabilities."""


    def __init__(self, server, access_token, debug=False):
        """
        Initialize class.

        :param server: String name of artifactory server
        :param access_token: String access token with sufficient permissions to repositories and artifacts of interest
        :param debug: Boolean whether to enable debug logging
        """
        self.server = server
        self.access_token = access_token
        self.headers = {'Authorization': f'Bearer {self.access_token}'}

        self.logger = logging.getLogger('logger')
        streamHandler = logging.StreamHandler()
        fileHandler = logging.FileHandler('log', encoding='utf-8')
        self.logger.addHandler(streamHandler)
        self.logger.addHandler(fileHandler)
        formatter = logging.Formatter('[%(asctime)s] [%(module)s.%(funcName)s] [%(levelname)s] %(message)s')
        streamHandler.setFormatter(formatter)
        fileHandler.setFormatter(formatter)

        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

    def test_connection(self):
        """
        Ensure Artifactory server responds without error.

        :returns: Boolean indicating success or failure
        """
        url = f'{self.server}'
        r = None
        try:
            r = requests.get(url, headers=self.headers)
        except requests.exceptions.MissingSchema:
            self.logger.error(f'please specify http or https schema with {self.server}')
            return False
        except requests.exceptions.ConnectionError:
            self.logger.error(f'error connecting to {self.server}')
            return False
        except requests.exceptions.TooManyRedirects:
            self.logger.error(f'too many redirects for {self.server}, bad url?')
            return False
        finally:
            if r:
                r.close()

        if r:
            if 200 <= r.status_code < 300:
                return True
            else:
                self.logger.error(f'test connection to {self.server} failed')
                return False

    def get_stats(self, artifact):
        """
        Get the statistics for an artifact.

        :param artifact: String artifact with full path to get statistics on
        :returns: Dictionary constaining stats
        :raises exception: if requests.exceptions.RequestException encountered, forwards it
        """
        safe_artifact = parse.quote(artifact)
        url = f'{self.server}/artifactory/api/storage/{safe_artifact}'
        r = None
        try:
            r = requests.get(url, headers=self.headers)
        except requests.exceptions.Timeout:
            self.logger.error(f'timeout connecting to {self.server}')
        except requests.exceptions.RequestException as e:
            self.logger.exception(f'unrecoverable exception {e} connecting to {self.server}')
        finally:
            if r:
                r.close()

        if r:
            if 200 <= r.status_code < 300:
                return r.json()
        else:
            self.logger.error(f'could not get stats for {artifact}')

    def get_trace(self, artifact):
        """
        Get the trace output for an artifact, indicating whether it can be downloaded without error.

        :param artifact: String artifact with full path that should be traced
        :returns: String text output of the result of the trace
        :raises exception: if requests.exceptions.RequestException encountered, forwards it
        """
        safe_artifact = parse.quote(artifact)
        url = f'{self.server}/artifactory/{safe_artifact}'
        params = {'skipUpdateStats': 'true', 'trace': 'null'}
        r = None
        try:
            r = requests.get(url, headers=self.headers, params=params)
        except requests.exceptions.Timeout:
            self.logger.error(f'timeout connecting to {self.server}')
        except requests.exceptions.RequestException as e:
            self.logger.exception(f'unrecoverable exception {e} connecting to {self.server}')
        finally:
            if r:
                r.close()

        if r:
            if 200 <= r.status_code < 300:
                return r.text
        else:
            self.logger.error(f'could not get trace for {artifact}, received {r.status_code}')

    def get_contents(self, repository):
        """
        List the contents of a repository.

        :param repository: String repository to list contents for
        :returns: Dictionary of contents for the repository
        :raises exception: if requests.exceptions.RequestException encountered, forwards it
        """
        safe_repository = parse.quote(repository)
        url = f'{self.server}/artifactory/api/storage/{safe_repository}'
        r = None
        params = {'list': 'null',
                  'deep': '1',
                  'listFolders': '0',
                  'mdTimestamps': '1',
                  'includeRootPath': '1'}
        try:
            r = requests.get(url, params=params, headers=self.headers)
        except requests.exceptions.Timeout:
            self.logger.error(f'timeout connecting to {self.server}')
        except requests.exceptions.RequestException as e:
            self.logger.exception(f'unrecoverable exception {e} connecting to {self.server}')
        finally:
            if r:
                r.close()

        if r:
            if 200 <= r.status_code < 300:
                return r.json()
        else:
            self.logger.error(f'could not get contents for {repository}')

    def del_artifact(self, artifact):
        """
        Remove an artifact unless that artifact is a folder; puts result in global List 'output.'

        :param artifact: String name of the artifact with full path to remove
        :raises exception: if requests.exceptions.RequestException encountered, forwards it
        """
        self.logger.debug(f'start remove artifact {artifact}')
        global output
        safe_artifact = parse.quote(artifact)
        if self.is_folder(safe_artifact):
            output.append((artifact, ARTIFACT_IS_FOLDER))
            self.logger.info(f'folder {artifact} will not be deleted')
            return
        url = f'{self.server}/artifactory/{safe_artifact}'
        r = None
        try:
            r = requests.delete(url, headers=self.headers)
        except requests.exceptions.Timeout:
            self.logger.error(f'timeout connecting to {self.server}')
        except requests.exceptions.RequestException as e:
            self.logger.exception(f'unrecoverable exception {e} connecting to {self.server}')
        finally:
            if r:
                r.close()
        if r:
            if 200 <= r.status_code < 300:
                output.append((artifact, ARTIFACT_DELETED))
                self.logger.info(f'deleted: {artifact}')
            else:
                output.append((artifact, ARTIFACT_NOT_DELETED))
                self.logger.error(f'could not delete artifact for {artifact}, received {r.status_code}')
        else:
            output.append((artifact, ARTIFACT_NOT_DELETED))
            self.logger.error(f'unrecoverable error for artifact {artifact}')

    def qdel_artifact(self, q, thread_no):
        """
        Threaded removal of artifacts in a queue.

        :param q: queue.Queue containing the String artifacts to remove
        :param thread_no: Integer thread number for logging
        """
        self.logger.info(f'started trace worker thread {thread_no}')
        while True:
            try:
                artifact = q.get()
            except Empty:
                continue
            else:
                self.del_artifact(artifact)
            q.task_done()

    def trace(self, artifact):
        """
        Trace an artifact; puts result in global List 'output.'

        :param artifact: String name of artifact with full path to trace
        """
        self.logger.debug(f'started remove artifact {artifact}')
        global output
        safe_artifact = parse.quote(artifact)
        trace = self.get_trace(safe_artifact)
        if trace:
            if trace.find(TRACE_SUCCESS) == -1:
                output.append((artifact, ARTIFACT_BAD))
                self.logger.info(f'{artifact}: {ARTIFACT_BAD}')
            else:
                output.append((artifact, ARTIFACT_GOOD))
                self.logger.debug(f'{artifact}: {ARTIFACT_GOOD}')
        else:
            output.append((artifact, ARTIFACT_UNKNOWN))
            self.logger.error(f'{artifact}: {ARTIFACT_UNKNOWN}')

    def qtrace(self, q, thread_no):
        """
        Threaded trace of artifacts in a queue.

        :param q: queue.Queue containing the String artifacts to trace
        :param thread_no: Integer thread number for logging
        """
        global output
        self.logger.info(f'started trace worker thread {thread_no}')
        while True:
            try:
                artifact = q.get()
            except Empty:
                continue
            else:
                self.trace(artifact)
            q.task_done()

    def is_folder(self, item):
        """
        Indicate if item is a folder (contains child key).

        :param item: String full path of item
        :returns: Boolean indicating if the item is a folder
        """
        stats = self.get_stats(item)
        if stats:
            if 'children' in stats.keys():
                self.logger.debug(f'detected folder: {item}')
                return True
            elif 'errors' in stats.keys():
                self.logger.error(f'errors detecting if {item} is a folder')
                return True
        self.logger.debug(f'detected non folder: {item}')
        return False

    def is_later(self, date1, date2):
        """
        Indicate if date1 is later in time than date2.

        :param date1: String in isoformat (artifactory dates are compatible)
        :param date2: String in isoformat (artifactory dates are compatible)
        :returns: Boolean, True if date1 is later in time, otherwise False
        """
        date1 = datetime.fromisoformat(date1.rstrip('Z'))
        date2 = datetime.fromisoformat(date2.rstrip('Z'))
        return date1 > date2

    def read_items(self, file):
        """
        Get items from a file, assumes they are one item per line.

        :param file: Path to the file
        :returns: List containing the items
        :raises: any exception that file like objects can throw would be raised here
        """
        content = ''
        if not isfile(file):
            self.logger.error(f'non file or cannot read {file}')
            exit(1)

        with open(file, 'r') as f:
            content = f.read()

        if content:
            return content.strip().split('\n')

    def cat_artifacts(self, repos, after):
        """
        Get all artifacts from repos and list them together in one object.

        :param repos: List of Strings name of repos to list artifacts from
        :param after: String in format of YYYY-MM-DD if provided only artifacts younger will be included
        :returns: List of artifacts from the repositories
        """
        artifacts = []
        rarts = []

        for repo in repos:
            ret = self.get_contents(repo)
            if ret:
                if after:
                    rarts = [ f'{repo}{art["uri"]}' for art in ret['files'] if not art['folder'] and self.is_later(art['lastModified'], after) ]
                else:
                    rarts = [ f'{repo}{art["uri"]}' for art in ret['files'] if not art['folder'] ]
            artifacts = artifacts + rarts
        return artifacts

    def compile_artifacts(self, repos=None, afile=None, rfile=None, after=None):
        """
        List artifacts from various sources.
        
        :param repos: List of strings with names of repos to list artifacts from
        :param afile: String name of file containing artifacts to include in output, one per line
        :param rfile: String name of file containing repos to list artifacts from, one per line
        :param after: String date in format YYYY-MM-DD if provided only artifacts younger will be included
        :returns: List of artifacts from the various sources, deduplicated
        """
        arts = []
        afile_arts = []
        rfile_arts = []

        self.logger.debug(f'compiling list of artifacts from repos {repos}, afile {afile}, and rfile {rfile}')
        if repos:
            arts = self.cat_artifacts(repos, after)

        if afile:
            afile_arts = self.read_items(afile)

        if rfile:
            rfile_repos = self.read_items(rfile)
            if rfile_repos:
                rfile_arts = self.cat_artifacts(rfile_repos, after)

        return list(set(arts + afile_arts + rfile_arts))

if __name__ == '__main__':
    arguments = docopt(__doc__, version='jfintegrity 1.0')

    ACCESS_TOKEN = arguments['--access-token']
    if not ACCESS_TOKEN:
        ACCESS_TOKEN = get_config('.access_token')

    BASE_URL = arguments['--url']
    if not BASE_URL:
        BASE_URL = get_config('.url')

    jfi = jfIntegrity(server=BASE_URL, access_token=ACCESS_TOKEN, debug=arguments['-V'])
    if not jfi.test_connection():
        print(f'could not connect to artifactory server...please check url')
        exit(1)

    q = Queue()
    if arguments['delete']:
        artifacts = jfi.read_items(arguments['DEL_FILE'])
        for i in range(int(arguments['--threads'])):
            worker = threading.Thread(target=jfi.qdel_artifact, args=(q, i,), daemon=True)
            worker.start()
    elif arguments['check']:
        after_date = arguments['--after']
        artifacts = jfi.compile_artifacts(repos=arguments['REPO'],
                                          afile=arguments['--afile'],
                                          rfile=arguments['--rfile'],
                                          after = after_date)

        for i in range(int(arguments['--threads'])):
            worker = threading.Thread(target=jfi.qtrace, args=(q, i,), daemon=True)
            worker.start()

    for artifact in artifacts:
        q.put(artifact)
    q.join()

    with open('traceable_artifacts', 'w') as f:
        for art in output:
            if art[1] == ARTIFACT_GOOD:
                f.write(f'{art[0]}\n')

    with open('untraceable_artifacts', 'w') as f:
        for art in output:
            if art[1] == ARTIFACT_BAD:
                f.write(f'{art[0]}\n')

    with open('trace_failure_artifacts', 'w') as f:
        for art in output:
            if art[1] == ARTIFACT_UNKNOWN:
                f.write(f'{art[0]}\n')