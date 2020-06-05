#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import json
import os
import plistlib
import re
import shlex
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pprint import pprint
from urllib.request import urlopen
from uuid import uuid4

from .utils import run_shell, timeit

CODESIGN_CREDS = os.path.expanduser('~/code-signing/cert-cred')
CODESIGN_CERT = os.path.expanduser('~/code-signing/maccert.p12')
# The apple id file contains the apple id and an app specific password which
# can be generated from appleid.apple.com
# Note that apple accounts require two-factor authentication which is currntly
# setup on ox and via SMS on my phone
APPLE_ID = os.path.expanduser('~/code-signing/apple-notarization-creds')
path_to_entitlements = os.path.expanduser('~/entitlements.plist')


def run(*args):
    if len(args) == 1 and isinstance(args[0], str):
        args = shlex.split(args[0])
    if subprocess.call(args) != 0:
        raise SystemExit('Failed: {}'.format(args))


@contextmanager
def make_certificate_useable():
    KEYCHAIN = tempfile.NamedTemporaryFile(suffix='.keychain',
                                           dir=os.path.expanduser('~'),
                                           delete=False).name
    os.remove(KEYCHAIN)
    KEYCHAIN_PASSWORD = '{}'.format(uuid4())
    # Create temp keychain
    run('security create-keychain -p "{}" "{}"'.format(KEYCHAIN_PASSWORD,
                                                       KEYCHAIN))
    # Append temp keychain to the user domain
    raw = subprocess.check_output(
        'security list-keychains -d user'.split()).decode('utf-8')
    existing_keychain = raw.replace('"', '').strip()
    run('security list-keychains -d user -s "{}" "{}"'.format(
        KEYCHAIN, existing_keychain))
    try:
        # Remove relock timeout
        run('security set-keychain-settings "{}"'.format(KEYCHAIN))
        # Unlock keychain
        run('security unlock-keychain -p "{}" "{}"'.format(
            KEYCHAIN_PASSWORD, KEYCHAIN))
        # Add certificate to keychain
        with open(CODESIGN_CREDS, 'r') as f:
            cert_pass = f.read().strip()
        # Add certificate to keychain and allow codesign to use it
        # Use -A instead of -T /usr/bin/codesign to allow all apps to use it
        run('security import {} -k "{}" -P "{}" -T "/usr/bin/codesign"'.format(
            CODESIGN_CERT, KEYCHAIN, cert_pass))
        raw = subprocess.check_output(
            ['security', 'find-identity', '-v', '-p', 'codesigning',
             KEYCHAIN]).decode('utf-8')
        cert_id = re.search(r'"([^"]+)"', raw).group(1)
        # Enable codesigning from a non user interactive shell
        run('security set-key-partition-list -S apple-tool:,apple: -s '
            f'-k "{KEYCHAIN_PASSWORD}" -D "{cert_id}" -t private "{KEYCHAIN}"')
        yield
    finally:
        # Delete temporary keychain
        run('security delete-keychain "{}"'.format(KEYCHAIN))


def codesign(items):
    if isinstance(items, str):
        items = [items]
    # If you get errors while codesigning that look like "A timestamp was
    # expected but not found" it means that codesign  failed to contact Apple's
    # time servers, probably due to network congestion
    #
    # --options=runtime enables the Hardened Runtime
    subprocess.check_call([
        'codesign', '--options=runtime', '--entitlements=' +
        path_to_entitlements, '--timestamp', '-s', 'Kovid Goyal'
    ] + list(items))


def verify_signature(appdir):
    run('codesign', '-vvv', '--deep', '--strict', appdir)
    run('spctl', '--verbose=4', '--assess', '--type', 'execute', appdir)


def create_entitlements_file(entitlements=None):
    with open(path_to_entitlements, 'wb') as f:
        f.write(plistlib.dumps(entitlements or {}))


def notarize_app(app_path):
    # See
    # https://developer.apple.com/documentation/xcode/notarizing_your_app_before_distribution/customizing_the_notarization_workflow?language=objc
    # and
    # https://developer.apple.com/documentation/xcode/notarizing_your_app_before_distribution/resolving_common_notarization_issues?language=objc
    with open(APPLE_ID) as f:
        un, pw = f.read().strip().split(':')

    with open(os.path.join(app_path, 'Contents', 'Info.plist'), 'rb') as f:
        primary_bundle_id = plistlib.load(f)['CFBundleIdentifier']

    zip_path = os.path.join(os.path.dirname(app_path), 'program.zip')
    print('Creating zip file for notarization')
    with timeit() as times:
        run('ditto', '-c', '-k', '--zlibCompressionLevel', '9', '--keepParent',
            app_path, zip_path)
    print('ZIP file of {} MB created in {} minutes and {} seconds'.format(
        os.path.getsize(zip_path) // 1024**2, *times))

    def altool(*args):
        args = ['xcrun', 'altool'
                ] + list(args) + ['--username', un, '--password', pw]
        p = subprocess.Popen(args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        output = stdout + '\n' + stderr
        print(output)
        if p.wait() != 0:
            print('The command {} failed with error code: {}'.format(
                args, p.returncode))
            try:
                run_shell()
            finally:
                raise SystemExit(1)
        return output

    print('Submitting for notarization')
    with timeit() as times:
        try:
            stdout = altool('--notarize-app', '-f', zip_path,
                            '--primary-bundle-id', primary_bundle_id)
        finally:
            os.remove(zip_path)
        request_id = re.search(r'RequestUUID = (\S+)', stdout).group(1)
        status = 'in progress'
    print('Submission done in {} minutes and {} seconds'.format(*times))

    print('Waiting for notarization')
    with timeit() as times:
        start_time = time.monotonic()
        while status == 'in progress':
            time.sleep(30)
            print(
                'Checking if notarization is complete,',
                'time elapsed: {:.1f} seconds'
                .format(time.monotonic() - start_time))
            stdout = altool('--notarization-info', request_id)
            status = re.search(r'Status\s*:\s+(.+)', stdout).group(1).strip()
    print('Notarization done in {} minutes and {} seconds'.format(*times))

    if status.lower() != 'success':
        log_url = re.search(r'LogFileURL\s*:\s+(.+)', stdout).group(1).strip()
        if log_url != '(null)':
            log = json.loads(urlopen(log_url).read())
            pprint(log)
        raise SystemExit('Notarization failed, see JSON log above')
    with timeit() as times:
        print('Stapling notarization ticket')
        run('xcrun', 'stapler', 'staple', '-v', app_path)
        run('xcrun', 'stapler', 'validate', '-v', app_path)
        run('spctl', '--verbose=4', '--assess', '--type', 'execute', app_path)
    print('Stapling took {} minutes and {} seconds'.format(*times))
