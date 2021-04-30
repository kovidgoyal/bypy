#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

from ..constants import ismacos, current_build_arch, UNIVERSAL_ARCHES
from ..utils import simple_build


needs_lipo = True


def main(args):
    ft = 'no' if ismacos else 'yes'
    ct = 'yes' if ismacos else 'no'
    configure = (
        '--disable-dependency-tracking --disable-static --with-glib=no'
        f' --with-freetype={ft} --with-gobject=no --with-cairo=no'
        f' --with-fontconfig=no --with-icu=no --with-coretext={ct}'
    ).split()
    if UNIVERSAL_ARCHES and 'arm' in current_build_arch():
        configure += [
            '--build=x86_64-apple-darwin', '--host=aarch64-apple-darwin',
            f'CFLAGS=-arch {current_build_arch()}',
            f'CXXFLAGS=-arch {current_build_arch()}',
        ]

    simple_build(configure)
