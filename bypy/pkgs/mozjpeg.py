#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import BIN, ismacos
from bypy.utils import (cmake_build, install_binaries, iswindows,
                        windows_cmake_build)


def main(args):
    if iswindows:
        windows_cmake_build()
        install_binaries('build/jpegtran-static.exe',
                         'bin',
                         fname_map=lambda x: 'jpegtran-calibre.exe')
        install_binaries('build/cjpeg-static.exe',
                         'bin',
                         fname_map=lambda x: 'cjpeg-calibre.exe')
    else:
        env = {}
        if ismacos:
            env['PATH'] = BIN + os.pathsep + os.environ['PATH']
        cmake_build(env=env)
