#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
from bypy.constants import PREFIX, iswindows, ismacos
from bypy.utils import (cmake_build, copy_headers, install_binaries,
                        replace_in_file, walk, windows_cmake_build)


def main(args):
    if iswindows:
        # cmake cannot find openssl
        replace_in_file(
            'CMakeLists.txt', 'FIND_PACKAGE(LIBCRYPTO)',
            ('SET(LIBCRYPTO_FOUND "1")\n'
             'SET(LIBCRYPTO_INCLUDE_DIR "{0}/include")\n'
             'SET(LIBCRYPTO_LIBRARIES "{0}/lib/libcrypto.lib")\n'
             'SET(PODOFO_HAVE_OPENSSL_1_1 "1")\n').format(
                 PREFIX.replace(os.sep, '/')))
        windows_cmake_build(
            WANT_LIB64='FALSE', PODOFO_BUILD_SHARED='TRUE',
            PODOFO_BUILD_STATIC='False',
            FREETYPE_INCLUDE_DIR=f"{PREFIX}/include/freetype2",
            nmake_target='podofo_shared'
        )
        copy_headers('build/podofo_config.h', 'include/podofo')
        copy_headers('src/podofo/*', 'include/podofo')
        for f in walk():
            if f.endswith('.dll'):
                install_binaries(f, 'bin')
            elif f.endswith('.lib'):
                install_binaries(f, 'lib')
    else:
        if ismacos:
            replace_in_file(
                'CMakeLists.txt', 'FIND_PACKAGE(FREETYPE REQUIRED)',
                (
                    'SET(FREETYPE_FOUND "1")\n'
                    'SET(FREETYPE_INCLUDE_DIR "{0}/include/freetype2")\n'
                    'SET(FREETYPE_LIBRARIES "{0}/lib/libfreetype.dylib")'
                ).format(PREFIX))
            replace_in_file(
                'src/podofo/base/PdfDate.cpp', 'struct tm _tm{}', 'struct tm _tm = {0}')

        cmake_build(
            make_args='podofo_shared',
            PODOFO_BUILD_LIB_ONLY='TRUE',
            PODOFO_BUILD_SHARED='TRUE',
            PODOFO_BUILD_STATIC='FALSE',
        )


def modify_excludes(excludes):
    excludes.discard('doc')
