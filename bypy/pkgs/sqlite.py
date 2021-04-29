#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from bypy.constants import CFLAGS, TARGETS, ismacos, iswindows
from bypy.utils import ModifiedEnv, arch_for_target, copy_headers, simple_build


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
        if len(TARGETS) > 1:
            env['CC'] = 'clang ' + ' '.join(
                f'-arch {arch_for_target(x)}' for x in TARGETS)
            env['CPP'] = 'clang -E'
    env['CFLAGS'] = cflags
    with ModifiedEnv(**env):
        simple_build('--disable-dependency-tracking --disable-static')
