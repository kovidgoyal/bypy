#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2021, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re
import shlex

from bypy.constants import (
    CFLAGS, CL, CPPFLAGS, LDFLAGS, current_build_arch,
    is_cross_half_of_lipo_build, ismacos, iswindows
)
from bypy.utils import copy_headers, install_binaries, replace_in_file, run

needs_lipo = True


def add_dll_exports():
    exp = '__declspec(dllexport)' if iswindows else \
        '__attribute__ ((visibility ("default")))'
    replace_in_file(
        'include/libstemmer.h',
        re.compile(r'^(.+)\(', re.M), fr'{exp} \1('
    )


def read_sources():
    for line in open('mkinc_utf8.mak'):
        line = line.strip().rstrip('\\').strip()
        if line.endswith('.c'):
            yield line


def main(args):
    add_dll_exports()
    objects = []
    cc = CL if iswindows else ('clang' if ismacos else 'gcc')
    cppflags = shlex.split(CPPFLAGS)
    cflags = shlex.split(CFLAGS)
    ldflags = shlex.split(LDFLAGS)
    if is_cross_half_of_lipo_build():
        cflags += ['-arch', current_build_arch()]
    for c in read_sources():
        obj = c.replace('.c', '.obj' if iswindows else '.o')
        objects.append(obj)
        if not iswindows:
            args = [cc] + cppflags + cflags + [
                '-O2', '-Iinclude', '-fPIC', '-fvisibility=hidden',
                '-c', c, '-o', obj]
            run(*args)
    if iswindows:
        dll = 'libstemmer.dll'
        args = ['/LD'] + list(read_sources()) + ['/Fe:' + dll]
        run(cc, *args)
        install_binaries(dll, 'bin')
        install_binaries('libstemmer.lib')
    else:
        ext = 'dylib' if ismacos else 'so'
        dll = f'libstemmer.0.{ext}' if ismacos else f'libstemmer.{ext}.0'
        args = ldflags
        if not ismacos:
            args += ['-Wl,-soname,libstemmer.so.0']
        if is_cross_half_of_lipo_build():
            args += ['-arch', current_build_arch()]
        run(
            cc, '-shared', '-o', dll, *args, *objects
        )
        os.symlink(dll, f'libstemmer.{ext}')
        install_binaries(dll)
        install_binaries(f'libstemmer.{ext}')
    copy_headers('include/libstemmer.h')
    if iswindows:
        os.chdir('/')
