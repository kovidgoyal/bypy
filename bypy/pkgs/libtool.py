#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import PREFIX, UNIVERSAL_ARCHES, build_dir
from bypy.utils import replace_in_file, simple_build, walk


def main(args):
    arches = ' '.join(f'-arch {x}' for x in UNIVERSAL_ARCHES)
    simple_build(('--program-prefix=g', f'CC=gcc {arches}', f'CXX=g++ {arches}', 'CPP=gcc -E', 'CXXCPP=g++ -E'))
    for path in walk(build_dir()):
        if path.endswith('/glibtoolize'):
            replace_in_file(path, build_dir(), PREFIX)
