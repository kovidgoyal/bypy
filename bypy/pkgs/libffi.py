#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import re
import os

from .constants import PREFIX, islinux, build_dir
from .utils import simple_build, replace_in_file


def main(args):
    simple_build('--disable-static --enable-pax_emutramp')
    if islinux:
        replace_in_file(os.path.join(build_dir(), 'lib/pkgconfig/libffi.pc'), re.compile(br'^prefix=.+$', re.M), b'prefix=%s' % PREFIX)
