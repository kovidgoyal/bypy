#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


from bypy.constants import iswindows
from bypy.utils import (cmake_build, install_binaries, replace_in_file,
                        windows_cmake_build)


def main(args):
    cmake_args = dict(ENABLE_CPP='0',
                      ENABLE_LIBOPENJPEG='none',
                      ENABLE_GLIB='OFF',
                      ENABLE_GOBJECT_INTROSPECTION='OFF',
                      ENABLE_CMS='none',
                      ENABLE_QT5='OFF',
                      ENABLE_LIBCURL='OFF',
                      BUILD_GTK_TESTS='OFF',
                      BUILD_QT5_TESTS='OFF',
                      BUILD_CPP_TESTS='OFF')
    # poppler unconditionally searches for cairo which we dont want
    replace_in_file('CMakeLists.txt',
                    'macro_optional_find_package(Cairo ${CAIRO_VERSION})',
                    'set(CAIRO_FOUND false)')
    if iswindows:
        windows_cmake_build(**cmake_args)
        install_binaries('build/utils/*.exe', 'bin')
    else:
        cmake_build(**cmake_args)
