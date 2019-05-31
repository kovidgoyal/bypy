#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import PREFIX, build_dir
from bypy.utils import replace_in_file, simple_build, walk


def main(args):
    simple_build()
    for path in walk(os.path.join(build_dir(), 'bin')):
        replace_in_file(path, build_dir(), PREFIX)
    for path in walk(build_dir()):
        if path.endswith('/autom4te.cfg'):
            replace_in_file(path, build_dir(), PREFIX)
