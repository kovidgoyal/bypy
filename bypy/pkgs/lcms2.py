#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import UNIVERSAL_ARCHES, current_build_arch, ismacos
from bypy.utils import simple_build

needs_lipo = True

if ismacos:
    def main(args):
        configure = []
        if UNIVERSAL_ARCHES and 'arm' in current_build_arch():
            configure += [
                '--build=x86_64-apple-darwin', '--host=aarch64-apple-darwin',
                f'CFLAGS=-arch {current_build_arch()}'
            ]
        simple_build(configure)
