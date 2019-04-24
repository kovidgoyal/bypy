#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import glob
import os
from .constants import PATCHES
from .utils import simple_build, apply_patch


def main(args):
    patches = glob.glob(os.path.join(PATCHES, 'readline??-???'))
    if not patches:
        raise SystemExit('Could not find readline patches')
    for p in sorted(patches):
        apply_patch(p, level=2)
    simple_build('--disable-static', make_args='SHLIB_LIBS=-lncursesw')
