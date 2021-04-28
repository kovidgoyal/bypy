#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import NMAKE, TARGETS, iswindows
from bypy.utils import (arch_for_target, copy_headers, install_binaries,
                        replace_in_file, run, simple_build)

if iswindows:
    def main(args):
        run(f'"{NMAKE}" -f win32/Makefile.msc')
        run(f'"{NMAKE}" -f win32/Makefile.msc test')
        install_binaries('zlib1.dll*', 'bin')
        install_binaries('zlib.lib'), install_binaries('zdll.*')
        copy_headers('zconf.h'), copy_headers('zlib.h')
else:
    def main(args):
        configure_args = []
        if TARGETS:
            replace_in_file(
                'configure',
                'CFLAGS="${CFLAGS} ${ARCHS}"',
                'CFLAGS="${CFLAGS} ${ARCHS}"\n  SFLAGS="${SFLAGS} ${ARCHS}"'
            )
            archs = ' '.join(f'-arch {arch_for_target(x)}' for x in TARGETS)
            configure_args.append(f'--archs={archs}')
        simple_build(configure_args)
