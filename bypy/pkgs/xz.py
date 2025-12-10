#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import CFLAGS, UNIVERSAL_ARCHES, ismacos
from bypy.utils import ModifiedEnv, simple_build


def main(args):
    cflags = CFLAGS
    env = {}
    if ismacos:
        if len(UNIVERSAL_ARCHES) > 1:
            env['CC'] = 'clang ' + ' '.join(
                f'-arch {x}' for x in UNIVERSAL_ARCHES)
            env['CPP'] = 'clang -E'
    env['CFLAGS'] = cflags
    with ModifiedEnv(**env):
        simple_build('--disable-dependency-tracking')
