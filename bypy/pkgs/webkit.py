#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from functools import partial

from bypy.constants import PREFIX, islinux, iswindows
from bypy.utils import apply_patch, cmake_build, replace_in_file

patch = partial(apply_patch, convert_line_endings=iswindows)


def main(args):
    # Control font hinting
    patch('webkit_control_hinting.patch')
    # Fix null point dereference (Fedora)
    # https://github.com/annulen/webkit/issues/573
    patch('qt5-webkit-null-pointer-dereference.patch', level=1)
    # Fix layout issues in trojita
    # https://github.com/annulen/webkit/issues/511
    patch('qt5-webkit-trojita-1.patch', level=1)
    patch('qt5-webkit-trojita-2.patch', level=1)

    # fix detection of python2
    if islinux:
        replace_in_file(
            'Source/cmake/WebKitCommon.cmake',
            'find_package(PythonInterp 2.7.0 REQUIRED)',
            'set(PYTHONINTERP_FOUND "ON")\n'
            'set(PYTHON_EXECUTABLE /usr/bin/python2)'
        )

    cmake_build(
        PORT='Qt', ENABLE_TOOLS='OFF', ENABLE_WEBKIT2='OFF',
        CMAKE_PREFIX_PATH='{0};{0}/qt'.format(PREFIX),
        # gstreamer is needed for audio/video on Linux
        USE_GSTREAMER='OFF',
        # libhyphen is needed for automatic hyphenation on Linux
        USE_LIBHYPHEN='OFF',
        # Dont build tests
        ENABLE_API_TESTS='OFF', ENABLE_TEST_SUPPORT='OFF',
        library_path=True
    )
