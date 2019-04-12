#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys
import tempfile

_plat = sys.platform.lower()
iswindows = 'win32' in _plat or 'win64' in _plat
ismacos = 'darwin' in _plat
islinux = not iswindows and not ismacos
del _plat


def uniq(vals):
    ''' Remove all duplicates from vals, while preserving order.  '''
    vals = vals or ()
    seen = set()
    seen_add = seen.add
    return list(x for x in vals if x not in seen and not seen_add(x))


def base_dir():
    ans = getattr(base_dir, 'ans', None)
    if ans is None:
        ans = base_dir.ans = os.path.abspath('bypy')
    return ans


ROOT = 'C:\\' if iswindows else '/'
is64bit = sys.maxsize > (1 << 32)
SW = ROOT + 'sw'
if iswindows:
    is64bit = os.environ['BUILD_ARCH'] == '64'
    SW += '64' if is64bit else '32'
BYPY = ROOT + 'bypy'
SRC = ROOT + 'src'
SOURCES = os.path.join(SRC, 'bypy', 'b', 'sources-cache')
PATCHES = os.path.join(BYPY, 'patches')
if iswindows:
    tempfile.tempdir = 'C:\\t\\t'
PREFIX = os.path.join(SW, 'sw')
BIN = os.path.join(PREFIX, 'bin')
PYTHON = os.path.join(
    PREFIX, 'private', 'python', 'python.exe') if iswindows else os.path.join(
            BIN, 'python')
cpu_count = os.cpu_count
worker_env = {}
cygwin_paths = []

if iswindows:
    CFLAGS = CPPFLAGS = LIBDIR = LDFLAGS = ''
    from vcvars import query_vcvarsall
    env = query_vcvarsall(is64bit)
    # Remove cygwin paths from environment
    paths = [p.replace('/', os.sep) for p in env['PATH'].split(os.pathsep)]
    cygwin_paths = [p for p in paths if 'cygwin64' in p.split(os.sep)]
    paths = [p for p in paths if 'cygwin64' not in p.split(os.sep)]
    # Add the bindir to the PATH, needed for loading DLLs
    paths.insert(0, os.path.join(PREFIX, 'bin'))
    paths.insert(0, os.path.join(PREFIX, 'qt', 'bin'))
    # Needed for pywintypes27.dll which is used by the win32api module
    paths.insert(0, os.path.join(
        PREFIX, r'private\python\Lib\site-packages\pywin32_system32'))
    os.environ['PATH'] = os.pathsep.join(uniq(paths))
    for k in env:
        if k != 'PATH':
            worker_env[k] = env[k]
    # The windows build machine has a very old/incomplete certificate store
    # In particular it is missing Let's Encrypt intermediate certs
    q = os.path.join(SRC, 'resources', 'mozilla-ca-certs.pem')
    if os.path.exists(q):
        os.environ['SSL_CERT_FILE'] = q
else:
    CFLAGS = worker_env['CFLAGS'] = '-I' + os.path.join(PREFIX, 'include')
    CPPFLAGS = worker_env['CPPFLAGS'] = '-I' + os.path.join(PREFIX, 'include')
    LIBDIR = os.path.join(PREFIX, 'lib')
    LDFLAGS = worker_env['LDFLAGS'] = f'-L{LIBDIR} -Wl,-rpath-link,{LIBDIR}'
