#!/usr/bin/env python
# License: GPLv3 Copyright: 2023, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import iswindows
from bypy.utils import (
    cmake_build, copy_headers, install_binaries, windows_cmake_build
)

if iswindows:
    def main(args):
        os.chdir('build/cmake')
        windows_cmake_build()
        install_binaries('build/lib/*.dll', 'bin')
        install_binaries('build/lib/*.lib')
        copy_headers('../../lib/*.h')
else:
    def main(args):
        os.chdir('build/cmake')
        cmake_build()
