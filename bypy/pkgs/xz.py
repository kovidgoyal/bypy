#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from bypy.constants import CFLAGS, TARGETS, ismacos
from bypy.utils import ModifiedEnv, arch_for_target, simple_build


def main(args):
    cflags = CFLAGS
    env = {}
    if ismacos:
        if len(TARGETS) > 1:
            env['CC'] = 'clang ' + ' '.join(
                f'-arch {arch_for_target(x)}' for x in TARGETS)
            env['CPP'] = 'clang -E'
    env['CFLAGS'] = cflags
    with ModifiedEnv(**env):
        simple_build('--disable-dependency-tracking')
