#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
from .constants import iswindows, PREFIX
from .utils import ModifiedEnv, python_build, python_install


def main(args):
    env = {}
    p = PREFIX.replace(os.sep, '/')
    env = dict(
        LIBXML_INCLUDE_DIRS='{0}/include{1}{0}/include/libxml2'.format(p, os.pathsep),
        LIBXML_LIB_DIRS='{0}/lib'.format(p),
        LIBXML_LIBS='libxml2' if iswindows else 'xml2',
    )
    with ModifiedEnv(**env):
        python_build()
    python_install()
