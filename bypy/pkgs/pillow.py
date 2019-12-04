#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import re

from bypy.constants import iswindows, PREFIX
from bypy.utils import replace_in_file, python_build, python_install


if iswindows:
    def main(args):
        root = (
            os.path.join(PREFIX, 'lib').replace('\\', '/'),
            os.path.join(PREFIX, 'include').replace('\\', '/')
        )
        replace_in_file(
            'setup.py',
            re.compile(r'^(JPEG|ZLIB|FREETYPE)_ROOT = None', re.M),
            fr'\1_ROOT = {root}')
        # dont link against static zlib
        replace_in_file(
            'setup.py', 'feature.zlib = "zlib"', 'feature.zlib = "zdll"')

        python_build()
        python_install()
