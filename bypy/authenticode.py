#!/usr/bin/env python
# License: GPLv3 Copyright: 2025, Kovid Goyal <kovid at kovidgoyal.net>

import os
import subprocess
import sys
import tempfile
import traceback
import uuid
from contextlib import suppress
from functools import lru_cache
from threading import Thread

OSSL = 'osslsigncode'
APPLICATION_NAME = 'calibre - E-book management'
APPLICATION_URL = 'https://calibre-ebook.com'


def set_application(name: str, url: str) -> None:
    global APPLICATION_NAME, APPLICATION_URL
    APPLICATION_NAME, APPLICATION_URL = name, url


@lru_cache
def file_as_astring(path: str) -> str:
    with open(path) as f:
        return f.read().rstrip()


class SigningFailed(Exception):
    pass


def sign_using_certificate(path: str) -> None:
    base = os.path.join(os.environ['PENV'], 'code-signing')
    output = path + '.signed'
    with suppress(FileNotFoundError):
        os.remove(output)
    cp = subprocess.run([
        OSSL, '-pkcs12', os.path.join(base, 'authenticode.pfx'), '-pass', file_as_astring(os.path.join(base, 'cert-cred')),
        '-n', APPLICATION_NAME, '-i', APPLICATION_URL, '-ts', 'http://timestamp.digicert.com', '-h', 'sha256',
        '-in', path, '-out', output
    ], stdout=subprocess.DEVNULL)
    if cp.returncode == 0:
        os.replace(output, path)
        return
    raise SigningFailed(f'Failed to sign {path} with osslsigncode return code: {cp.returncode}')


sign_path = sign_using_certificate


def is_signed(path: str) -> bool:
    tname = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex)
    cp = subprocess.run([OSSL, 'extract-signature', '-in', path, '-out', tname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with suppress(FileNotFoundError):
        os.remove(tname)
    return cp.returncode == 0


def ensure_signed(path: str) -> None:
    if is_signed(path):
        return
    sign_path(path)


def ensure_signed_in_tree(folder_path: str) -> None:
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            ext = f.lower().rpartition('.')
            if ext in ('dll', 'pyd', 'exe'):
                ensure_signed(os.path.join(dirpath, f))


class EnsureSignedInTree(Thread):

    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.exc: Exception | None = None
        self.tb = ''
        super().__init__(name='Authenticode', daemon=False)
        self.start()

    def run(self):
        try:
            ensure_signed_in_tree(self.folder_path)
        except SigningFailed as e:
            self.exc = e
        except Exception as e:
            self.exc = e
            self.tb = traceback.format_exc()

    def wait_till_finished(self) -> bool:
        self.join()
        return self.exc is None


if __name__ == '__main__':
    ensure_signed(sys.argv[-1])
