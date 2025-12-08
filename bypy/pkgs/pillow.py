#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re

from bypy.constants import PREFIX, iswindows
from bypy.utils import python_build, python_install, replace_in_file


def patch_for_windows():
        incdir = os.path.join(PREFIX, 'include')
        libdir = os.path.join(PREFIX, 'lib')
        with open('setup.cfg', 'a') as s:
            print(f'''
[build_ext]
include_dirs = {incdir}
library_dirs = {libdir}
enable_zlib = True
enable_jpeg = True
enable_webp = True
enable_webpmux = True
enable_freetype = True
''', file=s)

        replace_in_file('setup.py', 'DEBUG = False', 'DEBUG = True')
        replace_in_file('setup.py', '"libwebp"', '"libwebp_dll"')
        replace_in_file('setup.py', '"libwebpmux"', '"libwebpmux_dll"')
        replace_in_file('setup.py', '"libwebpdemux"', '"libwebpdemux_dll"')
        # dont link against static zlib
        replace_in_file(
            'setup.py', 'feature.zlib = "zlib"', 'feature.zlib = "zdll"')


def main(args):
    replace_in_file('src/PIL/features.py', re.compile(r'\{.+\.__file__\)\}'), '')
    if iswindows:
        patch_for_windows()
    python_build()
    python_install()
