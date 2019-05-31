#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import BIN, PREFIX, build_dir
from bypy.utils import ModifiedEnv, replace_in_file, simple_build, walk


def main(args):
    with ModifiedEnv(PATH=BIN + os.pathsep + os.environ['PATH']):
        simple_build()
    files = set()
    for path in walk(os.path.join(build_dir(), 'bin')):
        files.add(os.path.abspath(os.path.realpath(path)))
    for path in walk(build_dir()):
        if path.endswith('/Config.pm'):
            files.add(os.path.abspath(os.path.realpath(path)))
    for path in files:
        replace_in_file(path, build_dir(), PREFIX, missing_ok=True)
