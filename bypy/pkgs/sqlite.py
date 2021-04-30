#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from bypy.constants import CFLAGS, UNIVERSAL_ARCHES, ismacos, iswindows
from bypy.utils import ModifiedEnv, copy_headers, simple_build


def main(args):
    if iswindows:
        # On windows we dont actually build sqlite as the python build script
        # downloads its own version locked sqlite. We just install the headers
        copy_headers('sqlite3*.h')
        return
    cflags = CFLAGS
    env = {}
    if ismacos:
        cflags += ' -O2 -DSQLITE_ENABLE_LOCKING_STYLE'
        if len(UNIVERSAL_ARCHES) > 1:
            env['CC'] = 'clang ' + ' '.join(
                f'-arch {x}' for x in UNIVERSAL_ARCHES)
            env['CPP'] = 'clang -E'
    env['CFLAGS'] = cflags
    with ModifiedEnv(**env):
        simple_build('--disable-dependency-tracking --disable-static')
