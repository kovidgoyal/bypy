#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import PREFIX, build_dir
from bypy.utils import replace_in_file, simple_build, walk

needs_lipo = True


def main(args):
    simple_build('--program-prefix=g')
    for path in walk(build_dir()):
        if path.endswith('/glibtoolize'):
            replace_in_file(path, build_dir(), PREFIX)
