#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

from ..constants import ismacos
from ..utils import simple_build


def main(args):
    ft = 'no' if ismacos else 'yes'
    ct = 'yes' if ismacos else 'no'
    simple_build(
        '--disable-dependency-tracking --disable-static --with-glib=no'
        ' --with-freetype={} --with-gobject=no --with-cairo=no'
        ' --with-fontconfig=no --with-icu=no --with-coretext={}'
        .format(ft, ct))
