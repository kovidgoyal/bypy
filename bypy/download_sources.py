#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, NamedTuple
from urllib.request import urlopen, urlretrieve
from urllib.error import HTTPError

import tomllib

from .constants import OS_NAME, SOURCES, SRC, iswindows

DOWNLOAD_RETRIES = 3

class GlobalMetadata(NamedTuple):
    qt_version: str


def populate_qt_dep(dep, qt_version):
    f = dep['name'].replace('-', '')
    filename = f'{f}-everywhere-src-{qt_version}'
    p = qt_version.rpartition('.')[0]
    url = ('https://download.qt.io/official_releases/qt/'
           f'{p}/{qt_version}/submodules/{{filename}}')
    if 'unix' in dep['hashes']:
        dep['unix'] = {
            'filename': filename + '.tar.xz',
            'hash': dep['hashes']['unix'],
            'urls': [url],
        }
    if 'windows' in dep['hashes']:
        dep['windows'] = {
            'filename': filename + '.zip',
            'hash': dep['hashes']['windows'],
            'urls': [url],
        }


@dataclass
class Dependency:
    name: str
    version: str
    ecosystem: str = ''
    marker: str = ''
    allowed_os_names: tuple[str, ...] = ()
    urls: tuple[str, ...] = ()
    file_extension: str = ''
    expected_hash: str = ''

    @classmethod
    def from_sources_json_entry(self, e: dict[str, Any], global_metadata: GlobalMetadata) -> 'Dependency':
        name, version = e['name'].split(' ', 1)
        if name.startswith('qt-'):
            populate_qt_dep(e, global_metadata.qt_version)
        order = ('windows', 'unix') if iswindows else ('unix', 'windows')
        s = e.get(order[0], e.get(order[1]))
        assert s
        ext = s.get('file_extension', 'tar.gz').lstrip('.')
        filename = f'{name}-{version}.{ext}'
        urls = tuple(u.format(
            version=version, file_extension=ext, filename=filename, name=name,
            version_except_last=version.rpartition('.')[0],
            version_with_underscores=version.replace('.', '_').replace('-', '_'),
        ) for u in s['urls'])
        os = tuple(x.strip().lower() for x in e.get('os', '').split(',')) if e.get('os') else ()
        return Dependency(
            name=name, version=version, urls=urls, allowed_os_names=os, file_extension=ext,
            expected_hash=s['hash'],
        )

    @classmethod
    def from_pep_508(self, spec: str, global_metadata: GlobalMetadata) -> 'Dependency':
        spec, _, marker = spec.partition(';')
        parts = spec.split()
        name, version = parts[0], parts[-1]
        return Dependency(name=name, version=version, ecosystem='pypi', marker=marker)

    def is_buildable(self) -> bool:
        if self.allowed_os_names and OS_NAME not in self.allowed_os_names:
            return False
        if self.marker and not eval(self.marker, globals={}, locals={'sys_platform': sys.platform, 'os_name': os.name}):
            return False
        return True

    @property
    def _filename(self) -> str:
        return f'{self.name}-{self.version}.{self.file_extension}'

    @property
    def filename(self) -> str:
        if not self.file_extension:
            self.ensure_downloaded()
        return self._filename

    def ensure_pypi_downloaded(self) -> str:
        filename = self._filename
        path = os.path.join(SOURCES, filename)
        if os.path.exists(path):
            return path
        if not self.file_extension:
            for x in os.listdir(SOURCES):
                if x.startswith(filename):
                    self.file_extension = x[len(filename):]
                    return os.path.join(SOURCES, x)
        with urlopen(f'https://pypi.org/pypi/{self.name}/{self.version}/json') as f:
            metadata = json.loads(f.read())

        def commit(e: dict[str, Any], file_extension: str) -> str:
            self.urls = (e['url'],)
            self.file_extension = file_extension
            self.expected_hash = 'sha256:' + e['digests']['sha256']
            path = os.path.join(SOURCES, self._filename)
            download_pkg(self, path)
            return path

        for e in metadata['urls']:
            if e['packagetype'] == 'sdist':
                source = e
            elif e['packagetype'] == 'bdist_wheel' and e['filename'].endswith('none-any.whl'):
                return commit(e, 'whl')
        return commit(source, 'tar.' + source['filename'].rpartition('.')[-1])

    def verify_hash(self, path: str) -> bool:
        try:
            f = open(path, 'rb')
        except FileNotFoundError:
            return False
        alg, q = self.expected_hash.partition(':')[::2]
        q = q.strip()
        with f:
            h = getattr(hashlib, alg.lower())
            fhash = h(f.read()).hexdigest()
            return fhash == q

    def ensure_downloaded(self) -> str:
        if self.ecosystem == 'pypi':
            return self.ensure_pypi_downloaded()
        filename = self.filename
        path = os.path.join(SOURCES, filename)
        if self.verify_hash(path):
            return path
        download_pkg(self, path)
        return path


def read_python_deps(src: str, global_metadata: GlobalMetadata) -> tuple[list[Dependency], list[Dependency]]:
    with open(os.path.join(src, 'pyproject.toml'), 'rb') as f:
        data = tomllib.load(f)
    build_deps, runtime_deps = [], []
    for spec in data.get('build-system', {}).get('requires', ()):
        build_deps.append(Dependency.from_pep_508(spec, global_metadata))
    for spec in data.get('project', {}).get('dependencies', ()):
        runtime_deps.append(Dependency.from_pep_508(spec, global_metadata))
    return build_deps, runtime_deps


@lru_cache(2)
def read_deps(only_buildable: bool = False) -> tuple[Dependency, ...]:
    src = SRC if os.path.exists(SRC) else os.getcwd()
    with open(os.path.join(src, 'bypy', 'sources.json')) as f:
        base_data = json.load(f)
    dmap = {q['name'].partition(' ')[0]: q for q in base_data}
    qt_version = ''
    if qtb := dmap.get('qt-base'):
        qt_version = qtb['name'].partition(' ')[-1]
    gm = GlobalMetadata(qt_version=qt_version)
    python_build_deps, python_runtime_deps = read_python_deps(src, gm)
    data = []
    for dep in base_data:
        try:
            data.append(Dependency.from_sources_json_entry(dep, gm))
        except Exception as e:
            raise ValueError(f'Failed to parse Dependency: {dep} with error: {e}') from e
        if data[-1].name == 'python':
            data.extend(python_build_deps)
    data.extend(python_runtime_deps)
    if only_buildable:
        return tuple(d for d in data if d.is_buildable())
    return tuple(data)


@lru_cache()
def python_version() -> tuple[int, int]:
    for x in read_deps():
        if x.name == 'python':
            parts = x.version.split('.')
            return int(parts[0]), int(parts[1])
    raise KeyError('No python package found in sources.json')


def sha256_for_path(path: str) -> str:
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


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


def get_github_url(url):
    ident = url.split(':', maxsplit=1)[-1]
    return f'https://api.github.com/repos/{ident}/tarball'


def try_once(pkg: Dependency, url: str, path: str) -> None:
    if url.startswith('github:'):
        url = get_github_url(url)
    print('Downloading', os.path.basename(path), 'from', url)
    urlretrieve(url, path, reporthook())
    if not pkg.verify_hash(path):
        raise SystemExit(
            f'The hash of the downloaded file: {os.path.basename(path)}'
            ' does not match the saved hash. It\'s sha256 is'
            f': {sha256_for_path(path)}')


def download_pkg(pkg: Dependency, path: str) -> None:
    for try_count in range(DOWNLOAD_RETRIES):
        for url in pkg.urls:
            try:
                return try_once(pkg, url, path)
            except HTTPError as err:
                if err.code == 404:
                    raise
                import traceback
                traceback.print_exc()
                print(f'Download of {url} failed, with error: {err}', flush=True, file=sys.stderr)
            except Exception as err:
                import traceback
                traceback.print_exc()
                print(f'Download of {url} failed, with error: {err}', flush=True, file=sys.stderr)
            finally:
                print()
    raise SystemExit(
        f'Downloading of {pkg.name} failed after {DOWNLOAD_RETRIES} tries, giving up.')


def cleanup_cache(all_filenames: set[str]) -> None:
    if os.path.exists(SOURCES):
        existing = {x.lower(): x for x in os.listdir(SOURCES)}
        for extra in set(existing) - all_filenames:
            os.remove(os.path.join(SOURCES, existing[extra]))


def ensure_downloaded() -> None:
    all_filenames = set()
    for pkg in read_deps():
        all_filenames.add(os.path.basename(pkg.ensure_downloaded()).lower())
    cleanup_cache(all_filenames)
