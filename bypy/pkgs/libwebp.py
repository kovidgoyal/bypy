#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import iswindows, NMAKE
from bypy.utils import simple_build, run, install_binaries, copy_headers


needs_lipo = True


def main(args):
    if iswindows:
        run(
            f'"{NMAKE}" /f Makefile.vc CFG=release-dynamic'
            ' RTLIBCFG=dynamic OBJDIR=output UNICODE=1 all')
        install_binaries('output/release-dynamic/*/bin/*.dll', 'bin')
        install_binaries('output/release-dynamic/*/bin/*.exe', 'bin')
        install_binaries('output/release-dynamic/*/lib/*.lib', 'lib')
        install_binaries('output/release-dynamic/*/lib/*.exp', 'lib')
        copy_headers('src/webp')
    else:
        # mux/demux are needed for webengine
        simple_build(
            '--disable-dependency-tracking --disable-static'
            ' --enable-libwebpmux --enable-libwebpdemux')
