#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import hashlib
import json
import os
import re
import sys
import time
from base64 import standard_b64decode
from contextlib import suppress
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import count
from typing import Any, NamedTuple
from urllib.error import HTTPError
from urllib.request import urlopen, urlretrieve

import tomllib

from .constants import OS_NAME, SOURCES, SRC, iswindows

DOWNLOAD_RETRIES = 3

# data tables {{{
LICENSE_INFORMATION = {
    "nasm": ("BSD-2-Clause", 'nasm/netwide_assembler'),
    "cmake": ("BSD-3-Clause", 'cmake_project/cmake'),
    "autoconf": ("GPL-3.0-or-later", ''),
    "automake": ("GPL-2.0-or-later", ''),
    "libtool": ("LGPL-2.1-or-later", ''),
    "zlib": ("Zlib", 'zlib/zlib'),
    "bzip2": ("bzip2-1.0.6", 'bzip/bzip2'),
    "xz": ("0BSD", 'tukaani/xz'),
    "unrar": ("unrar", 'rarlab/unrar'),
    "brotli": ("MIT", 'google/brotli'),
    "libdeflate": ("MIT", ''),
    "zstd": ("BSD-2-Clause", ''),
    "expat": ("MIT", ''),
    "sqlite": ("blessing", 'sqlite/sqlite'),
    "libffi": ("MIT", ''),
    "hyphen": ("MPL-1.1", 'libffi_project/libffi'),
    "openssl": ("Apache-2.0", 'openssl/openssl'),
    "ncurses": ("MIT", 'gnu/ncurses'),
    "readline": ("GPL-3.0-only", 'gnu/readline'),
    "python": ("PSF-2.0", 'python/python'),
    "uchardet": ("Apache-2.0", ''),
    "icu": ("ICU", 'icu-project/international_components_for_unicode'),
    "libstemmer": ("BSD-2-Clause", ''),
    "libjpeg": ("IJG", 'libjpeg-turbo/libjpeg-turbo'),
    "libpng": ("libpng-2.0", 'libpng/libpng'),
    "libjbig": ("GPL-2.0-or-later", ''),
    "libtiff": ("libtiff", 'libtiff/libtiff'),
    "libwebp": ("Apache-2.0", 'webmproject/libwebp'),
    "jxrlib": ("BSD-2-Clause", ''),
    "freetype": ("FTL", 'freetype/freetype2'),
    "graphite": ("MIT", 'sil/graphite2'),
    "fontconfig": ("MIT", 'fontconfig_project/fontconfig'),
    "iconv": ("LGPL-2.0-only", ''),
    "libxml2": ("MIT", 'xmlsoft/libxml2'),
    "libxslt": ("MIT", 'xmlsoft/libxslt'),
    "chmlib": ("LGPL-2.1-or-later", ''),
    "optipng": ("Zlib", 'optipng_project/optipng'),
    "mozjpeg": ("IJG", 'mozilla/mozjpeg'),
    "libusb": ("LGPL-2.1-or-later", 'libusb/libusb'),
    "libmtp": ("LGPL-2.1-or-later", 'libmtp_project/libmtp'),
    "openjpeg": ("BSD-2-Clause", 'openjpeg/openjpeg'),
    "poppler": ("GPL-2.0-or-later", 'freedesktop/poppler'),
    "podofo": ("LGPL-2.0-or-later", 'podofo_project/podofo'),
    "libgpg-error": ("LGPL-2.1-or-later", 'gnupg/libgpg-error'),
    "libgcrypt": ("LGPL-2.1-or-later", 'gnupg/libgcrypt'),
    "glib": ("LGPL-2.1-or-later", 'gnome/glib'),
    "dbus": ("LGPL-2.1-or-later", 'freedesktop/dbus'),
    "dbusglib": ("GPL-2.0-or-later", 'freedesktop/dbus-glib'),
    "gnuwin32": ("GPL-2.0-only", ''),
    "hunspell": ("LGPL-2.1-or-later", 'hunspell_project/hunspell'),
    "ninja": ("Apache-2.0", ''),
    "nodejs": ("MIT", 'nodejs/node.js'),
    "nv-codec-headers": ("MIT", ''),
    "ffmpeg": ("LGPL-2.1-or-later", 'ffmpeg/ffmpeg'),
    "qt": ("GPL-3.0-only", ''),
    "speech-dispatcher-client": ("GPL-2.0-or-later", ''),
    "onnx": ("MIT", 'linuxfoundation/onnx'),
    "espeak": ("GPL-3.0-only", 'espeak-ng/espeak_ng'),
    "pkg-config": ("GPL-2.0-or-later", ''),
    "xkbcommon": ("X11", 'xkbcommon/libxkbcommon'),
    "libxxhash": ("BSD-2-Clause", ''),
    "xcrypt": ("LGPL-2.1-only", ''),
    "lcms2": ("MIT", 'littlecms/little_cms_color_engine'),
    "pcre": ("BSD-3-Clause", ''),
    "pixman": ("MIT", 'pixman/pixman'),
    "cairo": ("LGPL-2.1-only", 'cairographics/cairo'),
    "harfbuzz": ("MIT", 'harfbuzz_project/harfbuzz'),
    "simde": ("MIT", ''),
    "wayland": ("MIT", 'wayland/wayland'),
    "wayland-protocols": ("MIT", ''),
    "easylzma": ("BSD-2-Clause", ''),  # its actually public domain
}

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
    "MIT": "MIT",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "Common Development and Distribution License (CDDL)": "CDDL-1.0",
    "Eclipse Public License 1.0 (EPL-1.0)": "EPL-1.0",
    "Eclipse Public License 2.0 (EPL-2.0)": "EPL-2.0",
    "OSI Approved": "BSD-3-Clause",
    "any-OSI": "BSD-3-Clause",
}

PROJECT_LICENSE_MAP = {
    'pillow': 'MIT-CMU', # https://pypi.org/project/pillow/
    'zeroconf': "LGPL-2.1-or-later", # https://pypi.org/project/zeroconf/
    'setuptools': "MIT", # https://pypi.org/project/zeroconf/
}
# }}}

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


@lru_cache()
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


GO_PRIVATE_PACKAGES = {
    'github.com/kovidgoyal/exiffix': 'MIT',
}


@lru_cache()
def get_go_metadata(name: str, version: str) -> dict[str, str]:
    # Stupidly pkg.go.dev has no API: https://github.com/golang/go/issues/36785
    # you can get hash using: https://proxy.golang.org/{name}/@v/v{version}.info but not bothering
    # see endpoints at https://go.dev/ref/mod#goproxy-protocol
    cached = os.path.join(cache_dir(), f'go-{name.replace("/", "_")}-{version}.json')
    with suppress(FileNotFoundError), open(cached, 'rb') as f:
        return json.loads(f.read())
    try:
        with urlopen(f'https://pkg.go.dev/{name}') as f:
            raw = f.read().decode()
            if m := re.search(r'data-test-id="UnitHeader-license".+?>(.+?)<', raw, flags=re.DOTALL):
                ans = {'spdx_id': m.group(1).strip()}
            else:
                raise SystemExit(f'Could not find license for go package: {name}/{version}')
            with open(cached, 'w') as c:
                c.write(json.dumps(ans))
            return ans
    except Exception as err:
        raise SystemExit(f'Could not get go package: {name}/{version} with error: {err}') from err


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
    cpe: str = ''

    @classmethod
    def from_sources_json_entry(cls, e: dict[str, Any], global_metadata: GlobalMetadata) -> 'Dependency':
        name, _, version = e['name'].partition(' ')
        if name.startswith('qt-'):
            version = global_metadata.qt_version
            populate_qt_dep(e, version)
            spdx, purl = LICENSE_INFORMATION['qt']
            cpe_name = name.replace('-', '')
            cpe = f'cpe:2.3:a:qt:{cpe_name}:{version}:*:*:*:*:*:*:*'
            purl = f'pkg:generic/TheQtCompany/{cpe_name}@{version}'
        else:
            spdx, purl = LICENSE_INFORMATION[name]
            cpe = ''
            if purl:
                parts = purl.split('/')
                if len(parts) == 2:
                    purl = f'generic/{purl}'
                cpe = f'cpe:2.3:a:{parts[-2]}:{parts[-1]}:{version}:*:*:*:*:*:*:*'
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
            name=name, version=version, urls=urls, allowed_os_names=os, file_extension='.'+ext, cpe=cpe,
            expected_hash=s['hash'], _spdx_license_id=spdx, for_building=e.get('type') == 'build', purl=purl,
        )

    @classmethod
    def from_pep_508(cls, spec: str, global_metadata: GlobalMetadata, for_building: bool = False) -> 'Dependency':
        spec, _, marker = spec.partition(';')
        parts = spec.split()
        name, version = parts[0], parts[-1]
        return Dependency(name=name, version=version, ecosystem='pypi', marker=marker,
                          for_building=for_building, purl=f'pkg:pypi/{name}@{version}')

    @classmethod
    def from_go_sum(cls, name: str, version: str, alg: str) -> 'Dependency':
        alg, _, csum = alg.partition(':')
        if alg != 'h1':
            raise ValueError(f'Unkown checksum algorithm {alg} for go dep: {name}')
        csum = 'sha256:' + standard_b64decode(csum).hex()
        version = version[1:]
        purl = f'pkg:golang/{name}@{version}'
        if not (spdx := GO_PRIVATE_PACKAGES.get(name, '')):
            spdx = get_go_metadata(name, version)['spdx_id']
        return Dependency(
            name=name, version=version, purl=purl, ecosystem='go', expected_hash=csum, urls=('https://' + name,),
            _spdx_license_id=spdx,
        )

    def is_buildable(self) -> bool:
        if self.allowed_os_names and OS_NAME not in self.allowed_os_names:
            return False
        if self.marker and not eval(self.marker, {}, {'sys_platform': sys.platform, 'os_name': os.name}):
            return False
        return True

    @property
    def filename_prefix(self) -> str:
        name = self.name.lower()
        if self.ecosystem == 'pypi':
            # fucking python wheel filenames have to match the importable package name
            name = name.replace('-', '_')
        return f'{name}-{self.version}'

    @property
    def _filename(self) -> str:
        return self.filename_prefix + self.file_extension

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
        if self.cpe:
            refs.append({
                "referenceCategory": "SECURITY",
                "referenceType": "cpe23Type",
                "referenceLocator": self.cpe,
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
        match self.ecosystem:
            case 'pypi':
                self.ensure_pypi_download_data()
                return
            case 'go':
                return
        raise ValueError(f'No download URLs for {self.name}@{self.version}')

    def ensure_pypi_downloaded(self) -> str:
        filename = self._filename
        path = os.path.join(SOURCES, filename)
        if os.path.exists(path):
            return path
        if not self.file_extension:
            q = filename
            for x in os.listdir(SOURCES):
                if x.startswith(q):
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
def read_go_deps() -> list[Dependency]:
    ans = []
    package_hashes = {}
    package_go_mod_hashes = {}
    with suppress(FileNotFoundError), open('go.sum') as f:
        for line in f:
            name, version, alg = line.split()
            version, sep, q = version.partition('/')
            if sep == '/':
                if q == 'go.mod':
                    package_go_mod_hashes[name] = version, alg
                else:
                    raise ValueError(f'Unknown hash type: {q} for package: {name}')
            else:
                package_hashes[name] = version, alg
    for name in set(package_hashes) | set(package_go_mod_hashes):
        version, alg = package_hashes.get(name) or package_go_mod_hashes[name]
        ans.append(Dependency.from_go_sum(name, version, alg))
    return ans



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
