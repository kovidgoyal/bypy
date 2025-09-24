#!/usr/bin/env python
# License: GPLv3 Copyright: 2025, Kovid Goyal <kovid at kovidgoyal.net>

import os
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from contextlib import suppress
from functools import lru_cache
from threading import Event, Thread

OSSL = 'osslsigncode'
APPLICATION_NAME = 'calibre - E-book management'
APPLICATION_URL = 'https://calibre-ebook.com'
TIMESTAMP_SERVERS = (
    'http://timestamp.digicert.com',        # DigiCert
    'http://timestamp.acs.microsoft.com/',  # this is Microsoft Azure Code Signing
    'http://rfc3161.ai.moda/windows',       # this is a load balancer
    'http://timestamp.comodoca.com/rfc3161',
    'http://timestamp.sectigo.com'
)


def set_application(name: str, url: str) -> None:
    global APPLICATION_NAME, APPLICATION_URL
    APPLICATION_NAME, APPLICATION_URL = name, url


@lru_cache
def file_as_astring(path: str) -> str:
    with open(path) as f:
        return f.read().rstrip()


class SigningFailed(Exception):
    stderr: str

    def __init__(self, msg: str, stderr: str = ''):
        super().__init__(msg)
        self.stderr = stderr


def sign_using_certificate(path: str) -> None:
    base = os.path.join(os.environ['PENV'], 'code-signing')
    output = path + '.signed'
    with suppress(FileNotFoundError):
        os.remove(output)
    st = os.stat(path)
    cp = subprocess.run([
        OSSL, '-pkcs12', os.path.join(base, 'authenticode.pfx'), '-pass', file_as_astring(os.path.join(base, 'cert-cred')),
        '-n', APPLICATION_NAME, '-i', APPLICATION_URL, '-ts', TIMESTAMP_SERVERS[0], '-h', 'sha256',
        '-in', path, '-out', output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if cp.returncode == 0:
        os.replace(output, path)
        os.chmod(path, st.st_mode)
        return
    raise SigningFailed(
        f'Failed to sign {path} with osslsigncode return code: {cp.returncode}', cp.stderr.decode('utf-8', 'replace'))


sign_path = sign_using_certificate


def is_signed(path: str) -> bool:
    tname = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex)
    cp = subprocess.run([OSSL, 'extract-signature', '-in', path, '-out', tname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with suppress(FileNotFoundError):
        os.remove(tname)
    return cp.returncode == 0


def ensure_signed(path: str) -> bool:
    if is_signed(path):
        return False
    sign_path(path)
    return True


def ensure_signed_in_tree(folder_path: str, do_print: Event = Event()) -> int:
    count = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            ext = f.lower().rpartition('.')[-1]
            if ext in ('dll', 'pyd', 'exe'):
                if do_print.is_set():
                    print(f'Signing: {f}')
                if ensure_signed(os.path.join(dirpath, f)):
                    count += 1
    return count


class EnsureSignedInTree(Thread):

    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.exc: Exception | None = None
        self.tb = ''
        self.do_print = Event()
        self.signed_count = 0
        super().__init__(name='Authenticode', daemon=False)
        self.start_time = time.monotonic()
        self.start()

    def run(self):
        try:
            self.signed_count = ensure_signed_in_tree(self.folder_path, self.do_print)
        except SigningFailed as e:
            self.exc = e
            self.tb = e.stderr
        except Exception as e:
            self.exc = e
            self.tb = traceback.format_exc()
        self.end_time = time.monotonic()

    def wait_till_finished_or_exit(self) -> None:
        if self.is_alive():
            self.do_print.set()
        self.join()
        if self.exc is None:
            print(f'Signing took {self.end_time - self.start_time:.1f} seconds')
            return
        if self.tb:
            print(self.tb, file=sys.stderr)
        raise SystemExit(str(self.exc))


if __name__ == '__main__':
    ensure_signed(sys.argv[-1])
