#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import time
from urllib.parse import urljoin
from urllib.request import urlopen, urlretrieve
from functools import lru_cache

from .constants import SOURCES, iswindows, SRC, OS_NAME
from .utils import run, tempdir, walk

all_filenames = set()


def process_url(url, filename):
    return url.replace('{filename}', filename)


def add_filenames(item):
    for q in ('windows', 'unix'):
        q = item.get(q)
        if q is not None:
            all_filenames.add(q['filename'].lower())


def ok_dep(dep):
    os = dep.get('os')
    if os is not None:
        oses = {x.strip().lower() for x in os.split(',')}
        if OS_NAME not in oses:
            return False
    py = dep.get('python')
    if py is not None:
        return sys.version_info.major >= py
    return True


@lru_cache()
def read_deps(only_buildable=True):
    with open(os.path.join(SRC, 'bypy', 'sources.json')) as f:
        data = json.load(f)
    if only_buildable:
        return tuple(filter(ok_dep, data))
    ans = {}
    for item in data:
        add_filenames(item)
        if iswindows:
            s = item.get('windows') or item['unix']
        else:
            s = item['unix']
        s['name'] = item['name']
        s['urls'] = [process_url(x, s['filename']) for x in s['urls']]
        ans[s['name']] = s
    return ans


def verify_hash(pkg):
    fname = os.path.join(SOURCES, pkg['filename'])
    alg, q = pkg['hash'].partition(':')[::2]
    q = q.strip()
    matched = False
    try:
        f = open(fname, 'rb')
    except FileNotFoundError:
        pass
    else:
        with f:
            if alg == 'git':
                matched = True
            else:
                h = getattr(hashlib, alg.lower())
                fhash = h(f.read()).hexdigest()
                matched = fhash == q
    return matched


def reporthook():
    start_time = time.monotonic()

    def report(count, block_size, total_size):
        if count == 0:
            return
        duration = time.monotonic() - start_time
        if duration == 0:
            return
        progress_size = int(count * block_size)
        speed = int(progress_size / (1024 * duration))
        if total_size == -1:
            msg = '%d MB, %d KB/s, %d seconds passed' % (
                progress_size / (1024 * 1024), speed, duration)
        else:
            percent = int(count * block_size * 100 / total_size)
            msg = "%d%%, %d MB, %d KB/s, %d seconds passed" % (
                percent, progress_size / (1024 * 1024), speed, duration)
        sys.stdout.write('\r...' + msg)
        sys.stdout.flush()
    return report


def get_pypi_url(pkg):
    parts = pkg['filename'].split('-')
    pkg_name = '-'.join(parts[:-1])
    base = 'https://pypi.python.org/simple/%s/' % pkg_name
    raw = urlopen(base).read()
    for m in re.finditer((
        r'href="([^"]+%s)#sha256=.+"' % pkg['filename']).encode('utf-8'), raw
    ):
        return urljoin(base, m.group(1))
    raise ValueError('Failed to find PyPI URL for {}'.format(pkg))


def get_git_clone(pkg, url, fname):
    with tempdir('git-') as tdir:
        run('git clone --depth=1 ' + url, cwd=tdir)
        ddir = os.listdir(tdir)[0]
        with open(os.path.join(tdir, ddir, '.git', 'HEAD'), 'rb') as f:
            ref = f.read().decode('utf-8').partition(' ')[-1].strip()
        with open(os.path.join(tdir, ddir, '.git', ref), 'rb') as f:
            h = f.read().decode('utf-8').strip()
        fhash = pkg['hash'].partition(':')[-1]
        if h != fhash:
            raise SystemExit(
                f'The hash of HEAD for {pkg["name"]} has changed')
        fdir = os.path.join(tdir, ddir)
        for f in walk(os.path.join(fdir, '.git')):
            os.chmod(f, 0o666)  # Needed to prevent shutil.rmtree from failing
        shutil.rmtree(os.path.join(fdir, '.git'))
        with tarfile.open(fname, 'w:bz2') as tf:
            tf.add(fdir, arcname=ddir)
        shutil.rmtree(fdir)


def try_once(pkg, url):
    filename = pkg['filename']
    fname = os.path.join(SOURCES, filename)
    if url == 'pypi':
        url = get_pypi_url(pkg)
    print('Downloading', filename, 'from', url)
    if pkg['hash'].startswith('git:'):
        get_git_clone(pkg, url, fname)
    else:
        urlretrieve(url, fname, reporthook())
    if not verify_hash(pkg):
        raise SystemExit(
            f'The hash of the downloaded file: {filename}'
            ' does not match the saved hash')


def download_pkg(pkg):
    for try_count in range(3):
        for url in pkg['urls']:
            try:
                return try_once(pkg, url)
            except Exception as err:
                import traceback
                traceback.print_exc()
                sys.stderr.flush()
                print(f'Download of {url} failed, with error: {err}')
                sys.stdout.flush()
            finally:
                print()
    raise SystemExit(
        'Downloading of %s failed after three tries, giving up.' % pkg['name'])


def cleanup_cache():
    if os.path.exists(SOURCES):
        existing = {x.lower(): x for x in os.listdir(SOURCES)}
        for extra in set(existing) - all_filenames:
            os.remove(os.path.join(SOURCES, existing[extra]))


def download(pkgs=None):
    sources = read_deps(only_buildable=False)
    cleanup_cache()
    for name, pkg in sources.items():
        if not pkgs or name in pkgs:
            if not verify_hash(pkg):
                download_pkg(pkg)


def filename_for_dep(dep):
    sources = read_deps(only_buildable=False)
    return sources[dep]['filename']
