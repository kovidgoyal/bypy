#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import PREFIX, ismacos, iswindows
from bypy.utils import (cmake_build, install_binaries, replace_in_file,
                        windows_cmake_build)


def main(args):
    cmake_args = dict(
        ENABLE_CPP='0',
        ENABLE_GLIB='OFF',
        ENABLE_GOBJECT_INTROSPECTION='OFF',
        ENABLE_CMS='none',
        ENABLE_QT5='OFF',
        ENABLE_QT6='OFF',
        ENABLE_BOOST='OFF',
        ENABLE_LIBCURL='OFF',
        BUILD_GTK_TESTS='OFF',
        BUILD_QT5_TESTS='OFF',
        BUILD_CPP_TESTS='OFF',
    )
    # poppler unconditionally searches for cairo which we dont want
    replace_in_file('CMakeLists.txt',
                    'macro_optional_find_package(Cairo ${CAIRO_VERSION})',
                    'set(CAIRO_FOUND false)')
    if ismacos:
        replace_in_file('CMakeLists.txt',
                        'macro_optional_find_package(NSS3)',
                        'set(NSS3_FOUND false)')
    if iswindows:
        cmake_win_args= dict (
            FREETYPE_INCLUDE_DIRS=os.path.join(PREFIX, 'include', 'freetype2'),
            FREETYPE_LIBRARY=os.path.join(PREFIX, 'lib', 'freetype.lib'),
            JPEG_INCLUDE_DIR=os.path.join(PREFIX, 'include'),
            JPEG_LIBRARY=os.path.join(PREFIX, 'lib', 'jpeg.lib'),
            PNG_LIBRARY=os.path.join(PREFIX, 'lib', 'libpng16.lib'),
            PNG_PNG_INCLUDE_DIR=os.path.join(PREFIX, 'include'),
            ZLIB_INCLUDE_DIR=os.path.join(PREFIX, 'include'),
            ZLIB_LIBRARY=os.path.join(PREFIX, 'lib', 'zdll.lib'),
        )
        cmake_args.update(cmake_win_args)
        opjinc = f'{PREFIX}/include/openjpeg'.replace('\\', '/')
        opjlib = f'{PREFIX}/lib/openjp2.lib'.replace('\\', '/')
        replace_in_file(
            'CMakeLists.txt',
            'find_package(OpenJPEG)',
            'set(OpenJPEG_FOUND true)\n'
            'set(OPENJPEG_MAJOR_VERSION 2)\n'
            f'set(OPENJPEG_INCLUDE_DIRS {opjinc})\n'
        )
        replace_in_file(
            'CMakeLists.txt',
            'set(poppler_LIBS ${poppler_LIBS} openjp2)',
            'set(poppler_LIBS ${poppler_LIBS} %s)' % opjlib
        )
        replace_in_file(  # even though optional searching for it requires pkg-config causing failure
            'CMakeLists.txt',
            'macro_optional_find_package(NSS3)', '')
        windows_cmake_build(**cmake_args)
        install_binaries('build/utils/*.exe', 'bin')
        install_binaries('build/*.dll', 'bin')
        install_binaries('build/*.lib', 'lib')
    else:
        cmake_build(**cmake_args)


def install_name_change(old_name, is_dep):
    bn = os.path.basename(old_name)
    if bn.startswith('libpoppler'):
        return os.path.join(PREFIX, 'lib', bn)
    return old_name
