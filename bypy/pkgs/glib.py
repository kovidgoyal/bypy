#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import re
import os

from .constants import LIBDIR, PREFIX, build_dir
from .utils import simple_build, ModifiedEnv, replace_in_file


def main(args):
    with ModifiedEnv(LD_LIBRARY_PATH=LIBDIR):
        simple_build('--disable-dependency-tracking --disable-static --disable-selinux --disable-fam --with-libiconv=gnu --with-pcre=internal')
    replace_in_file(os.path.join(build_dir(), 'lib/pkgconfig/glib-2.0.pc'), re.compile(br'^prefix=.+$', re.M), b'prefix=%s' % PREFIX)
