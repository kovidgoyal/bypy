#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
from functools import partial

from bypy.constants import PREFIX, build_dir, islinux, iswindows
from bypy.utils import apply_patch, cmake_build, replace_in_file, walk

patch = partial(apply_patch, convert_line_endings=iswindows)


def main(args):
    # Control font hinting
    patch('webkit_control_hinting.patch')

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
        # No video
        ENABLE_VIDEO='OFF',
        # gstreamer is needed for audio/video on Linux
        USE_GSTREAMER='OFF',
        # libhyphen is needed for automatic hyphenation on Linux
        USE_LIBHYPHEN='OFF',
        # Dont build tests
        ENABLE_API_TESTS='OFF', ENABLE_TEST_SUPPORT='OFF',
        override_prefix=os.path.join(build_dir(), 'qt'),
        library_path=True
    )

    for path in walk(build_dir()):
        if path.endswith('.pri'):
            replace_in_file(path, build_dir(), PREFIX)
