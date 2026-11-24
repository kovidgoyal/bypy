#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import BIN, PREFIX, build_dir, ismacos
from bypy.utils import ModifiedEnv, replace_in_file, simple_build, walk


def main(args):
    env = {'PATH': BIN + os.pathsep + os.environ['PATH']}
    if ismacos:
        # The m4 shipped with Xcode is too old, use the one we built
        env['M4'] = os.path.join(BIN, 'm4')
    with ModifiedEnv(**env):
        simple_build()
    for path in walk(os.path.join(build_dir(), 'bin')):
        replace_in_file(path, build_dir(), PREFIX)
    for path in walk(build_dir()):
        if path.endswith('/autom4te.cfg'):
            replace_in_file(path, build_dir(), PREFIX)
