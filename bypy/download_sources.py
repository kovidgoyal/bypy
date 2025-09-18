#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import hashlib
from contextlib import suppress
import json
import os
import sys
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, NamedTuple
from urllib.request import urlopen, urlretrieve
from urllib.error import HTTPError
from itertools import count

import tomllib

from .constants import OS_NAME, SOURCES, SRC, iswindows

DOWNLOAD_RETRIES = 3

class GlobalMetadata(NamedTuple):
    qt_version: str


def populate_qt_dep(dep, qt_version):
    f = dep['name'].partition(' ')[0].replace('-', '')
    filename = f'{f}-everywhere-src-{qt_version}'
    p = qt_version.rpartition('.')[0]
    url = ('https://download.qt.io/official_releases/qt/'
           f'{p}/{qt_version}/submodules/{filename}.tar.xz')
    dep['unix'] = {
        'file_extension': 'tar.xz',
        'hash': dep['hashes']['unix'],
        'urls': [url],
    }


@lru_cache(2)
def cache_dir() -> str:
    ans = os.path.join(os.path.expanduser('~'), '.cache', 'bypy')
    os.makedirs(ans, exist_ok=True)
    return ans


@lru_cache(2)
def get_pypi_metadata(name: str, version: str) -> dict[str, Any]:
    cached = os.path.join(cache_dir(), f'pypi-{name}-{version}.json')
    with suppress(FileNotFoundError), open(cached, 'rb') as f:
        return json.loads(f.read())
    try:
        with urlopen(f'https://pypi.org/pypi/{name}/{version}/json') as f:
            raw = f.read()
            with open(cached, 'wb') as c:
                c.write(raw)
            return json.loads(raw)
    except Exception as err:
        raise SystemExit(f'Could not get pypi package: {name}/{version} with error: {err}') from err


CLASSIFIER_TO_SPDX_MAP = {
    "BSD License": "BSD-3-Clause",
    "BSD": "BSD-3-Clause",
    "BSD-3-Clause": "BSD-3-Clause",
    "BSD-2-Clause": "BSD-2-Clause",
    "Apache Software License": "Apache-2.0",
    "GNU GPL 3": "GPL-3.0-only",
    "GPL": "GPL-2.0-or-later",
    "GNU General Public License v2 (GPLv2)": "GPL-2.0-only",
    "GNU General Public License v3 (GPLv3)": "GPL-3.0-only",
    "GPL v3": "GPL-3.0-only",
    "GNU Affero General Public License v3": "AGPL-3.0-only",
    "GNU Lesser General Public License v2.1 (LGPLv2.1)": "LGPL-2.1-only",
    "GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0-only",
    "GNU Lesser General Public License v2 or later (LGPLv2+)": "GPL-2.0-or-later",
    "GNU General Public License v3 or later (GPLv3+)": "GPL-3.0-or-later",
    "LGPL 3.0 or later": "LGPL-3.0-or-later",
    "LGPL-2.1-or-later": "LGPL-2.1-or-later",
    'ISC License (ISCL)': 'ISC',
    "MIT License": "MIT",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "Common Development and Distribution License (CDDL)": "CDDL-1.0",
    "Eclipse Public License 1.0 (EPL-1.0)": "EPL-1.0",
    "Eclipse Public License 2.0 (EPL-2.0)": "EPL-2.0",
    "OSI Approved": "BSD-3-Clause",
}

PROJECT_LICENSE_MAP = {
    'pillow': 'MIT-CMU', # https://pypi.org/project/pillow/
    'zeroconf': "LGPL-2.1-or-later", # https://pypi.org/project/zeroconf/
}

list_counter = count(1)


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
    unique_id_in_list: int = field(default_factory=lambda: next(list_counter))
    for_building: bool = False
    _spdx_license_id: str = ''
    purl: str = ''

    @classmethod
    def from_sources_json_entry(self, e: dict[str, Any], global_metadata: GlobalMetadata) -> 'Dependency':
        name, _, version = e['name'].partition(' ')
        if name.startswith('qt-'):
            version = global_metadata.qt_version
            populate_qt_dep(e, version)
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
            expected_hash=s['hash'], _spdx_license_id=e['spdx'], for_building=e.get('type') == 'build',
        )

    @classmethod
    def from_pep_508(self, spec: str, global_metadata: GlobalMetadata, for_building: bool = False) -> 'Dependency':
        spec, _, marker = spec.partition(';')
        parts = spec.split()
        name, version = parts[0], parts[-1]
        return Dependency(name=name, version=version, ecosystem='pypi', marker=marker,
                          for_building=for_building, purl=f'pkg:pypi/{name}@{version}')

    def is_buildable(self) -> bool:
        if self.allowed_os_names and OS_NAME not in self.allowed_os_names:
            return False
        if self.marker and not eval(self.marker, {}, {'sys_platform': sys.platform, 'os_name': os.name}):
            return False
        return True

    @property
    def filename_prefix(self) -> str:
        return f'{self.name}-{self.version}'

    @property
    def _filename(self) -> str:
        if not (s := self.file_extension).startswith('-'):
            s = '.' + s
        return self.filename_prefix + s

    @property
    def filename(self) -> str:
        if not self.file_extension:
            self.ensure_downloaded()
        return self._filename

    def fetch_license_from_pypi(self) -> None:
        data = get_pypi_metadata(self.name, self.version)
        if (le := data.get('info', {}).get('license_expression')):
            self._spdx_license_id = le
            return
        if (license_info := data.get('info', {}).get('license')) and (sid := CLASSIFIER_TO_SPDX_MAP.get(license_info)):
            self._spdx_license_id = sid
            return
        classifiers = data.get('info', {}).get('classifiers', [])
        license_classifiers = [c.split('::')[-1].strip() for c in classifiers if c.startswith('License :: OSI Approved')]
        for q in license_classifiers:
            if val := CLASSIFIER_TO_SPDX_MAP.get(q):
                self._spdx_license_id = val
                break
        else:
            if (le := PROJECT_LICENSE_MAP.get(self.name)):
                self._spdx_license_id = le
                return
            which = '\n'.join(license_classifiers or classifiers)
            raise ValueError(f'No recognizable pypi license information for {self.name}@{self.version}: {which}')

    @property
    def spdx_license_id(self) -> str:
        if not self._spdx_license_id:
            if self.ecosystem == 'pypi':
                self.fetch_license_from_pypi()
            else:
                raise ValueError(f'No license information for {self.name}@{self.version}')
        return self._spdx_license_id

    @property
    def sbom_spdx(self) -> dict[str, Any]:
        self.ensure_download_data()
        alg, _, val = self.expected_hash.partition(':')
        refs = []
        if self.purl:
            refs.append({
                "referenceCategory": "PACKAGE-MANAGER",
                "referenceType": "purl",
                "referenceLocator": self.purl,
            })
        return {
            "name": self.name,
            "SPDXID": f"SPDXRef-Package-{self.unique_id_in_list}",
            "versionInfo": self.version,
            "downloadLocation": self.urls[0],
            "filesAnalyzed": False,
            "licenseConcluded": self.spdx_license_id,
            "licenseDeclared": self.spdx_license_id,
            "checksums": [{'algorithm': alg.upper(), 'checksumValue': val}],
            "externalRefs": refs,
        }

    def ensure_pypi_download_data(self) -> None:
        def commit(e: dict[str, Any], file_extension: str) -> str:
            self.urls = (e['url'],)
            self.file_extension = file_extension
            self.expected_hash = 'sha256:' + e['digests']['sha256']
            path = os.path.join(SOURCES, self._filename)
            return path

        metadata = get_pypi_metadata(self.name, self.version)
        for e in metadata['urls']:
            if e['packagetype'] == 'sdist':
                source = e
            elif e['packagetype'] == 'bdist_wheel' and e['filename'].endswith('-none-any.whl'):
                suffix = '-' + '-'.join(e['filename'].split('-')[-3:])
                commit(e, suffix)
                return
        commit(source, 'tar.' + source['filename'].rpartition('.')[-1])

    def ensure_download_data(self) -> None:
        if self.urls:
            return
        if self.ecosystem == 'pypi':
            self.ensure_pypi_download_data()
            return
        raise ValueError(f'No download URLs for {self.name}@{self.version}')

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
        self.ensure_pypi_download_data()
        path = os.path.join(SOURCES, self._filename)
        download_pkg(self, path)
        return path

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
        build_deps.append(Dependency.from_pep_508(spec, global_metadata, True))
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
                    raise SystemExit(f'Download of {url} failed, with error: {err}') from err
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


def cleanup_cache(all_filename_prefixes: set[str]) -> None:

    def matches_prefix(x: str) -> bool:
        for q in all_filename_prefixes:
            if x.startswith(q):
                return True
        return False

    if os.path.exists(SOURCES):
        for not_needed in (x for x in os.listdir(SOURCES) if not matches_prefix(x)):
            print('Removing obsolete source file:', not_needed)
            os.unlink(os.path.join(SOURCES, not_needed))


def ensure_downloaded() -> None:
    all_filename_prefixes = set()
    for pkg in read_deps():
        pkg.ensure_downloaded()
        all_filename_prefixes.add(pkg.filename_prefix)
    cleanup_cache(all_filename_prefixes)
