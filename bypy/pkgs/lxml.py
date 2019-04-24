#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os

from .constants import PREFIX, PYTHON, iswindows
from .utils import python_build, run, replace_in_file, python_install


def main(args):
    if iswindows:
        # libxml2 does not depend on iconv in our windows build
        replace_in_file('setupinfo.py', ", 'iconv'", '')
        run(PYTHON, *('setup.py build_ext -I {0}/include;{0}/include/libxml2 -L {0}/lib'.format(PREFIX.replace(os.sep, '/')).split()))
    else:
        run(PYTHON, *('setup.py build_ext -I {0}/include/libxml2 -L {0}/lib'.format(PREFIX).split()), library_path=True)
    python_build()
    python_install()
