#!/usr/bin/env python
# License: GPLv3 Copyright: 2025, Kovid Goyal <kovid at kovidgoyal.net>

import atexit
import os
import struct
import subprocess
import sys
import tempfile
import time
import traceback
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from functools import lru_cache
from threading import Event, Thread
from typing import NamedTuple
from urllib.parse import quote, quote_from_bytes

OSSL = 'osslsigncode'
HSM_SUBJECT_NAME = 'Kovid Goyal'
APPLICATION_NAME = 'calibre - E-book management'
APPLICATION_URL = 'https://calibre-ebook.com'
TIMESTAMP_SERVERS = (
    'http://timestamp.digicert.com',        # DigiCert
    'http://timestamp.acs.microsoft.com/',  # this is Microsoft Azure Code Signing
    'http://rfc3161.ai.moda/windows',       # this is a load balancer
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


class HSMData(NamedTuple):
    token_pin: str = ''
    path_to_full_chain_of_certs: str = ''
    hsm_private_key_uri: str = ''
    path_to_pkcs11_module: str =  '/usr/lib/libeToken.so'


@lru_cache(2)
def initialize_hsm() -> HSMData:
    import PyKCS11  # type: ignore
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    base = os.path.join(os.environ['PENV'], 'code-signing')
    ans = HSMData(file_as_astring(os.path.join(base, 'hsm-token-password')).strip())

    pkcs11 = PyKCS11.PyKCS11Lib()
    pkcs11.load(ans.path_to_pkcs11_module)
    slots = pkcs11.getSlotList(tokenPresent=True)
    if not slots:
        raise SystemExit('No slots found, is the USB token connected?')
    # use the first slot
    slot = slots[0]
    session = pkcs11.openSession(slot, PyKCS11.CKF_SERIAL_SESSION)
    token_info = pkcs11.getTokenInfo(slot)
    @contextmanager
    def sm() -> Iterator[None]:
        try:
            session.login(ans.token_pin)
            try:
                yield None
            finally:
                session.logout()
        finally:
            session.closeSession()

    with sm():
        subject_map = {}
        chain: list[x509.Certificate] = []
        cert_objects = session.findObjects([
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE),
            (PyKCS11.CKA_CERTIFICATE_TYPE, PyKCS11.CKC_X_509),
        ])
        for co in cert_objects:
            cert_der = bytes(session.getAttributeValue(co, [PyKCS11.CKA_VALUE])[0])
            cert = x509.load_der_x509_certificate(cert_der)
            s = cert.subject.rfc4514_string()
            subject_map[cert.subject] = cert
            if f'CN={HSM_SUBJECT_NAME},' in s and not chain:
                chain.append(cert)
                key_objects = session.findObjects([
                    (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
                ])
                for k in key_objects:
                    dk = k.to_dict()
                    if (key_label := dk.get('CKA_LABEL')) == HSM_SUBJECT_NAME:
                        token_label = token_info.label.strip()
                        uri_path = [
                            f"token={quote(token_label)}",
                            f"object={quote(key_label)}",
                            f"id={quote_from_bytes(bytes(dk['CKA_ID']))}", # CKA_ID is hex-encoded and then percent-encoded
                            "type=private"
                        ]
                        ans = ans._replace(hsm_private_key_uri=f"pkcs11:{';'.join(uri_path)}")
        if not chain:
            subjects = '\n'.join(s.rfc4514_string() for s in subject_map)
            raise SystemExit(f'No certificate with the subject {HSM_SUBJECT_NAME} found on token. Available certificates are:\n{subjects}')
        current = chain[0]
        while True:
            parent = subject_map.get(current.issuer)
            if parent is None or parent is current:
                break
            chain.append(parent)
            current = parent
        with tempfile.NamedTemporaryFile(suffix='.pem', prefix='bypy-hsm-certs-', delete=False) as t:
            atexit.register(os.remove, t.name)
            for cert in chain:
                t.write(cert.public_bytes(serialization.Encoding.PEM))
        ans = ans._replace(path_to_full_chain_of_certs=t.name)
    return ans


def sign_using_hsm(path: str) -> None:
    output = path + '.signed'
    with suppress(FileNotFoundError):
        os.remove(output)
    st = os.stat(path)
    hsm = initialize_hsm()

    cp = subprocess.run([
        OSSL, 'sign',
        '-engine', '/usr/lib/engines-3/pkcs11.so', '-pkcs11module', hsm.path_to_pkcs11_module,
        '-certs', hsm.path_to_full_chain_of_certs, '-key', hsm.hsm_private_key_uri, '-pass', hsm.token_pin,
        '-n', APPLICATION_NAME, '-i', APPLICATION_URL, '-h', 'sha256',
        '-ts', TIMESTAMP_SERVERS[0], '-ts', TIMESTAMP_SERVERS[1], '-ts', TIMESTAMP_SERVERS[2],
        '-in', path, '-out', output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if cp.returncode == 0:
        os.replace(output, path)
        os.chmod(path, st.st_mode)
        return
    raise SigningFailed(
        f'Failed to sign {path} with osslsigncode return code: {cp.returncode}', cp.stderr.decode('utf-8', 'replace'))


sign_path = sign_using_hsm


IMAGE_DIRECTORY_ENTRY_SECURITY = 4
PE32_MAGIC = 0x10b
PE32PLUS_MAGIC = 0x20b


def has_signature(file_path: str) -> bool:
    """
    Robustly and quickly checks if a PE file contains a digital signature
    block by parsing the PE header and checking if the image signature block
    exists and has a non-zero size. Returns False on any parsing error.
    """
    with open(file_path, 'rb') as f:
        if f.read(2) != b'MZ':
            return False
        f.seek(60)
        try:
            e_lfanew, = struct.unpack('<I', f.read(4))
        except Exception:
            return False

        # PE Header
        f.seek(e_lfanew)
        if f.read(4) != b'PE\0\0':
            return False

        # 4. Optional Header and Data Directories
        f.seek(20, os.SEEK_CUR)
        optional_header_start = f.tell()
        f.seek(optional_header_start)
        try:
            magic, = struct.unpack('<H', f.read(2))
        except Exception:
            return False
        f.seek(optional_header_start)

        if magic == PE32_MAGIC:
            f.seek(92, os.SEEK_CUR)
        elif magic == PE32PLUS_MAGIC:
            f.seek(108, os.SEEK_CUR)
        else:
            return False
        try:
            num, = struct.unpack('<I', f.read(4))
        except Exception:
            return False
        if num <= IMAGE_DIRECTORY_ENTRY_SECURITY:
            return False

        # The data directories immediately follow the optional header
        sizeof_image_data_directory = 8
        f.seek(sizeof_image_data_directory * IMAGE_DIRECTORY_ENTRY_SECURITY + 4, os.SEEK_CUR)
        try:
            size, = struct.unpack('<I', f.read(4))
        except Exception:
            return False
        return size > 0


def check_all_files_in_folder_are_signed(path: str) -> None:
    rc = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fpath = os.path.join(dirpath, f)
            if f.rpartition('.')[-1].lower() in ('exe', 'pyd', 'dll') and not has_signature(fpath):
                print('Unsigned:', fpath, file=sys.stderr)
                rc = 1
    raise SystemExit(rc)


def ensure_signed(path: str) -> bool:
    if has_signature(path):
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


def has_valid_signature(path: str) -> bool:
    return subprocess.run([OSSL, 'verify', path], capture_output=True).returncode == 0


def verify_path(path: str) -> None:
    print(f'{path}: signature is {"valid" if has_valid_signature(path) else "not valid!"}')


def verify_tree(root_folder: str) -> None:
    invalid = []
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for f in filenames:
            if f.rpartition('.')[-1].lower() in ('exe', 'pyd', 'dll', 'msi'):
                path = os.path.join(dirpath, f)
                count += 1
                if not has_valid_signature(path):
                    invalid.append(path)
                    print(f'{path} does not have a valid signature')
    if invalid:
        print(f'{len(invalid)} invalid signatures out of {count} files')
    else:
        print(f'Checked {count} files, all have valid signatures.')
    raise SystemExit(1 if invalid else 0)


if __name__ == '__main__':
    is_dir = os.path.isdir(sys.argv[-1])
    if 'verify' in sys.argv:
        if is_dir:
            verify_tree(sys.argv[-1])
        else:
            verify_path(sys.argv[-1])
    else:
        try:
            if is_dir:
                do_print = Event()
                do_print.set()
                ensure_signed_in_tree(sys.argv[-1], do_print)
            else:
                ensure_signed(sys.argv[-1])
        except SigningFailed as e:
            if e.stderr:
                print(end=e.stderr, file=sys.stderr)
            raise SystemExit(str(e))
