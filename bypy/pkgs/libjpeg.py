#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import iswindows, is64bit
from bypy.utils import cmake_build, windows_cmake_build, replace_in_file


def main(args):
    if not iswindows:
        return cmake_build(WITH_JPEG8='1', ENABLE_STATIC='0')
    cpu = 'x86_64' if is64bit else 'i386'
    replace_in_file(
        'CMakeLists.txt',
        'string(TOLOWER ${CMAKE_SYSTEM_PROCESSOR} CMAKE_SYSTEM_PROCESSOR_LC)',
        f'set(CMAKE_SYSTEM_PROCESSOR_LC "{cpu}")')
    windows_cmake_build(
        WITH_JPEG8='1',
        ENABLE_STATIC='0',
        binaries='jpeg8.dll',
        libraries='jpeg.lib',
        headers='jconfig.h ../jerror.h ../jpeglib.h ../jmorecfg.h',
    )
