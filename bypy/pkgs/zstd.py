#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import NMAKE, UNIVERSAL_ARCHES, iswindows
from bypy.utils import (copy_headers, install_binaries,
                        replace_in_file, run, simple_build)

if iswindows:
    def main(args):
        install_binaries('dll/zstd.dll*', 'bin')
        install_binaries('static/libzstd_static.lib')
        copy_headers('include/zstd.h')
else:
    def main(args):
        configure_args = []
        if len(UNIVERSAL_ARCHES) > 1:
            replace_in_file(
                'configure',
                'CFLAGS="${CFLAGS} ${ARCHS}"',
                'CFLAGS="${CFLAGS} ${ARCHS}"\n  SFLAGS="${SFLAGS} ${ARCHS}"'
            )
            archs = ' '.join(f'-arch {x}' for x in UNIVERSAL_ARCHES)
            configure_args.append(f'--archs={archs}')
        simple_build(configure_args)
