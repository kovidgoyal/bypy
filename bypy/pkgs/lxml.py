#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>


import os

from bypy.constants import PREFIX, PYTHON, iswindows
from bypy.utils import python_build, python_install, replace_in_file, run


def main(args):
    if iswindows:
        # libxml2 does not depend on iconv in our windows build
        replace_in_file('setupinfo.py', ", 'iconv'", '')
        run(PYTHON, *('setup.py build_ext -I {0}/include;{0}/include/libxml2 -L {0}/lib'.format(PREFIX.replace(os.sep, '/')).split()))
    else:
        run(PYTHON, *('setup.py build_ext -I {0}/include/libxml2 -L {0}/lib'.format(PREFIX).split()), library_path=True)
    python_build()
    python_install()
