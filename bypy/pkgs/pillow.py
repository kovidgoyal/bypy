#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import iswindows, PREFIX
from bypy.utils import replace_in_file, python_build, python_install


if iswindows:
    def main(args):
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

        python_build()
        python_install()
