#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import iswindows
from bypy.utils import (cmake_build, copy_headers, install_binaries,
                        windows_cmake_build)


def main(args):
    cmake_args = dict(BUILD_CODEC='OFF')
    if iswindows:
        windows_cmake_build(**cmake_args)
        install_binaries('build/bin/*.dll', 'bin')
        install_binaries('build/bin/*.lib', 'lib')
        copy_headers('src/lib/openjp2/opj_*.h', 'include/openjpeg')
        copy_headers('build/src/lib/openjp2/opj_*.h', 'include/openjpeg')
        copy_headers('src/lib/openjp2/openjpeg.h', 'include/openjpeg')
    else:
        cmake_build(**cmake_args)
