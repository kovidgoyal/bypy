#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import ismacos
from bypy.utils import (cmake_build, install_binaries, iswindows,
                        windows_cmake_build, build_dir)


needs_lipo = True


def main(args):
    if iswindows:
        windows_cmake_build(ENABLE_SHARED='FALSE')
        install_binaries('build/jpegtran-static.exe',
                         'bin',
                         fname_map=lambda x: 'jpegtran-calibre.exe')
        install_binaries('build/cjpeg-static.exe',
                         'bin',
                         fname_map=lambda x: 'cjpeg-calibre.exe')
    else:
        kw = {}
        if ismacos:
            kw['PNG_SUPPORTED'] = 'FALSE'
        cmake_build(
            ENABLE_SHARED='FALSE',
            override_prefix=os.path.join(build_dir(), 'private', 'mozjpeg'), **kw
        )
