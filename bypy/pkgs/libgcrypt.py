#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

from .constants import PREFIX, is64bit
from .utils import simple_build


def main(args):
    cmd = '--disable-dependency-tracking --disable-static --with-libgpg-error-prefix=' + PREFIX
    if not is64bit:
        cmd += ' --disable-amd64-as-feature-detection --disable-pclmul-support'
    simple_build(cmd)
