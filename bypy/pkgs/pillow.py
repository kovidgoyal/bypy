#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import re

from .constants import iswindows, PREFIX
from .utils import replace_in_file, python_build, python_install


if iswindows:
    def main(args):
        root = repr((os.path.join(PREFIX, 'lib'), os.path.join(PREFIX, 'include')))
        replace_in_file('setup.py', re.compile(r'^(JPEG|ZLIB|FREETYPE)_ROOT = None', re.M), r'\1_ROOT = %s' % root)
        python_build()
        python_install()
