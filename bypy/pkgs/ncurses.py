#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

from .constants import PKG_CONFIG_PATH
from .utils import simple_build


def main(args):
    simple_build('--with-shared --without-debug --without-ada --enable-widec --with-normal --enable-pc-files --with-pkg-config-libdir=%s' % PKG_CONFIG_PATH)


def filter_pkg(parts):
    return 'terminfo' in parts or 'tabset' in parts or 'bin' in parts
