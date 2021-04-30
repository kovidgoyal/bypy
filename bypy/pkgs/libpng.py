#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import (PREFIX, UNIVERSAL_ARCHES, current_build_arch,
                            iswindows)
from bypy.utils import simple_build, windows_cmake_build

needs_lipo = True


def main(args):
    if iswindows:
        windows_cmake_build(
            PNG_SHARED='1', ZLIB_INCLUDE_DIR=os.path.join(PREFIX, 'include'),
            ZLIB_LIBRARY=os.path.join(PREFIX, 'lib', 'zdll.lib'),
            binaries='libpng*.dll', libraries='libpng*.lib',
            headers='pnglibconf.h ../png.h ../pngconf.h'
        )
    else:
        configure_args = ['--disable-dependency-tracking', '--disable-static']
        if UNIVERSAL_ARCHES and 'arm' in current_build_arch():
            configure_args += [
                '--build=x86_64-apple-darwin', '--host=aarch64-apple-darwin',
                f'CFLAGS=-arch {current_build_arch()}'
            ]
            if 'arm' in current_build_arch():
                # does not build with it set to on, or not set
                # https://github.com/glennrp/libpng/issues/257
                configure_args.append('--enable-arm-neon=off')
        simple_build(configure_args)
