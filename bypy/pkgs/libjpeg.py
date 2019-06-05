#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import iswindows
from bypy.utils import cmake_build, windows_cmake_build


def main(args):
    if iswindows:
        windows_cmake_build(
            WITH_JPEG8='1',
            binaries='sharedlib/jpeg8.dll*',
            libraries='sharedlib/jpeg.lib',
            headers='jconfig.h ../jerror.h ../jpeglib.h ../jmorecfg.h',
        )
    else:
        cmake_build(WITH_JPEG8='1',)
