#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>


import os

from bypy.constants import NMAKE, PREFIX, ismacos, iswindows
from bypy.utils import (
    cmake_build, install_binaries, install_tree, replace_in_file, run,
    simple_build, walk
)


def main(args):
    if iswindows:
        run(*(
            'cscript.exe configure.js include={0}/include'
            ' include={0}/include/libxml2 lib={0}/lib prefix={0}'
            ' zlib=yes iconv=yes'.format(
                PREFIX.replace(os.sep, '/')).split()), cwd='win32')
        for f in walk('.'):
            bname = os.path.basename(f)
            if bname.startswith('Makefile'):
                replace_in_file(f, '/OPT:NOWIN98', '', missing_ok=True)
                if bname == 'Makefile.msvc':
                    replace_in_file(f, 'iconv.lib', 'libiconv.lib')
            # elif bname == 'xsltconfig.h':
            #     replace_in_file(f, '@WITH_PROFILER@', '1')
        run(f'"{NMAKE}" /f Makefile.msvc', cwd='win32')
        install_tree('libxslt', 'include')
        install_tree('libexslt', 'include')
        for f in walk('.'):
            if f.endswith('.dll'):
                install_binaries(f, 'bin')
            elif f.endswith('.lib'):
                install_binaries(f)
    elif ismacos:
        cmake_build(
            LIBXSLT_WITH_PYTHON='OFF', LIBXML2_INCLUDE_DIR=f'{PREFIX}/include',
            relocate_pkgconfig=False
        )
    else:
        simple_build(
            '--disable-dependency-tracking --disable-static'
            ' --enable-shared --without-python --without-debug')
