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
from os.path import isfile
from helpers import get_config
from datetime import datetime
from sys import exit

TRACE_SUCCESS = "Request succeeded"
ARTIFACT_GOOD = 'artifact_traceable'
ARTIFACT_BAD = 'artifact_untraceable'
ARTIFACT_UNKNOWN = 'trace_failure'
ARTIFACT_DELETED = 'artifact_deleted'
ARTIFACT_NOT_DELETED = 'artifact_not_deleted'
ARTIFACT_IS_FOLDER = 'artifact_is_folder'

class jfIntegrity():

    def __init__(self, server, access_token, debug=False):
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
        
        self.test_connection()

    def test_connection(self):
        url = f'{self.server}/artifactory/api'
        r = None
        try:
            r = requests.get(url, headers=self.headers)
        except requests.exceptions.ConnectionError:
            self.logger.exception(f'error connecting to {self.server}')
            exit(1)
        except requests.exceptions.TooManyRedirects:
            self.logger.error(f'too many redirects for {self.server}, bad url?')
            exit(1)
        finally:
            if r:
                r.close()

    def get_stats(self, artifact):
        url = f'{self.server}/artifactory/api/storage/{artifact}'
        try:
            r = requests.get(url, headers=self.headers)
        except requests.exceptions.Timeout:
            self.logger.error(f'timeout connecting to {self.server}')
        except requests.exceptions.RequestException:
            self.logger.exception(f'unrecoverable exception {e} connecting to {self.server}')
        finally:
            r.close()

        if r:
            if 200 <= r.status_code < 300:
                return r.json()
        else:
            self.logger.error(f'could not get stats for {artifact}, received {r.status_code}')

    def get_trace(self, artifact):
        url = f'{self.server}/artifactory/{artifact}'
        params = {'skipUpdateStats': 'true', 'trace': 'null'}
        try:
            r = requests.get(url, headers=self.headers, params=params)
        except requests.exceptions.Timeout:
            self.logger.error(f'timeout connecting to {self.server}')
        except requests.exceptions.RequestException:
            self.logger.exception(f'unrecoverable exception {e} connecting to {self.server}')
        finally:
            r.close()

        if r:
            if 200 <= r.status_code < 300:
                return r.text
        else:
            self.logger.error(f'could not get trace for {artifact}, received {r.status_code}')

    def get_contents(self, repository):
        url = f'{self.server}/artifactory/api/storage/{repository}'
        params = {'list': 'null',
                  'deep': '1',
                  'listFolders': '0',
                  'mdTimestamps': '1',
                  'includeRootPath': '1'}
        try:
            r = requests.get(url, params=params, headers=self.headers)
        except requests.exceptions.Timeout:
            self.logger.error(f'timeout connecting to {self.server}')
        except requests.exceptions.RequestException:
            self.logger.exception(f'unrecoverable exception {e} connecting to {self.server}')
        finally:
            r.close()

        if r:
            if 200 <= r.status_code < 300:
                return r.json()
        else:
            self.logger.error(f'could not get contents for {repository}, received {r.status_code}')

    def del_artifact(self, q, thread_no):
        global output
        self.logger.info(f'started trace worker thread {thread_no}')
        while True:
            try:
                artifact = q.get()
            except Empty:
                continue
            else:
                if self.is_folder(artifact):
                    output.append((artifact, ARTIFACT_IS_FOLDER))
                    self.logger.info(f'folder {artifact} will not be deleted')
                url = f'{self.server}/artifactory/{artifact}'
                try:
                    r = requests.delete(url, headers=self.headers)
                except requests.exceptions.Timeout:
                    self.logger.error(f'timeout connecting to {self.server}')
                except requests.exceptions.RequestException:
                    self.logger.exception(f'unrecoverable exception connecting to {self.server}')
                finally:
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

    def trace(self, q, thread_no):
        global output
        self.logger.info(f'started trace worker thread {thread_no}')
        while True:
            try:
                artifact = q.get()
            except Empty:
                continue
            else:
                trace = self.get_trace(artifact)
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
            q.task_done()

    def is_folder(self, item):
        stats = self.get_stats(item)
        if stats:
            if 'children' in stats.keys():
                self.logger.debug(f'detected folder: {item}')
                return True
        self.logger.debug(f'detected non folder: {item}')
        return False

    def is_later(self, date1, date2):
        date1 = datetime.fromisoformat(date1.rstrip('Z'))
        date2 = datetime.fromisoformat(date2.rstrip('Z'))
        return date1 > date2

    def read_items(self, file):
        if not isfile(file):
            return None
        
        with open(file, 'r') as f:
            content = f.read()

        return content.strip().split('\n')

    def cat_artifacts(self, repos, after):
        artifacts = []
        rarts = []

        for repo in repos:
            ret = self.get_contents(repo)
            if ret:
                if after:
                    rarts = [ f'{repo}{art["uri"]}' for art in ret['files'] if not art['folder'] and self.is_later(art['lastModified'], after) ]
            artifacts = artifacts + rarts
        return artifacts

    def compile_artifacts(self, repos=None, afile=None, rfile=None, after=None):
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
    output = []
    after_date = ''

    arguments = docopt(__doc__, version='jfintegrity 1.0')

    ACCESS_TOKEN = arguments['--access-token']
    if not ACCESS_TOKEN:
        ACCESS_TOKEN = get_config('.access_token')

    BASE_URL = arguments['--url']
    if not BASE_URL:
        BASE_URL = get_config('.url')

    jfi = jfIntegrity(server=BASE_URL, access_token=ACCESS_TOKEN, debug=arguments['-V'])

    q = Queue()
    if arguments['delete']:
        pass
        #artifacts = jfi.read_items(arguments['DEL_FILE'])
        #for i in range(int(arguments['--threads'])):
        #    worker = threading.Thread(target=jfi.del_artifact, args=(q, i,), daemon=True)
        #    worker.start()
    elif arguments['check']:
        after_date = arguments['--after']
        artifacts = jfi.compile_artifacts(repos=arguments['REPO'],
                                          afile=arguments['--afile'],
                                          rfile=arguments['--rfile'],
                                          after = after_date)

        for i in range(int(arguments['--threads'])):
            worker = threading.Thread(target=jfi.trace, args=(q, i,), daemon=True)
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