#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>


import os
import re

from bypy.constants import LIBDIR, NMAKE, PREFIX, build_dir, ismacos, iswindows
from bypy.utils import (
    install_binaries, install_tree, replace_in_file, run, simple_build, walk, cmake_build
)

def main(args):
    if iswindows:
        run(*('cscript.exe configure.js include={0}/include'
            ' lib={0}/lib prefix={0} zlib=yes iconv=yes'.format(
                PREFIX.replace(os.sep, '/')).split()), cwd='win32')
        replace_in_file('win32/Makefile.msvc', 'iconv.lib', 'libiconv.lib')
        run(f'"{NMAKE}" /f Makefile.msvc', cwd='win32')
        install_tree('include/libxml', 'include/libxml2')
        for f in walk('.'):
            if f.endswith('.dll'):
                install_binaries(f, 'bin')
            elif f.endswith('.lib'):
                install_binaries(f)
    elif ismacos:
        cmake_build(
            LIBXML2_WITH_ICU='ON', LIBXML2_WITH_PYTHON='OFF', LIBXML2_WITH_TESTS='OFF',
            LIBXML2_WITH_LZMA='OFF',
        )
    else:
        # ICU is needed to use libxml2 in qt-webengine
        env = {}
        if ismacos:
            env['ICU_CFLAGS'] = f'-I{PREFIX}/include'
            env['ICU_LIBS'] = f'-L{LIBDIR} -licuc -licudata'
            env['ICU_DEFS'] = '-DDUMMY_DEF_FOR_STUPID_CONFIGURE_SCRIPT'
        simple_build(
            '--disable-dependency-tracking --disable-static --enable-shared'
            ' --without-python --without-debug --with-iconv={0} --disable-silent-rules'
            ' --with-zlib={0} --with-icu'.format(PREFIX), env=env)
        for path in walk(build_dir()):
            if path.endswith('/xml2-config'):
                replace_in_file(
                    path, re.compile(b'(?m)^prefix=.+'),
                    f'prefix={PREFIX}')
