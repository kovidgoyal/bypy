#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import NMAKE, UNIVERSAL_ARCHES, build_dir, iswindows, MAKEOPTS
from bypy.utils import (copy_headers, install_binaries,
                        replace_in_file, run, simple_build)

if iswindows:
    def main(args):
        install_binaries('dll/zstd.dll*', 'bin')
        install_binaries('static/libzstd_static.lib')
        copy_headers('include/zstd.h')
else:
    def main(args):
        run('make', MAKEOPTS)
        run('make', 'DESTDIR={}'.format(build_dir()), 'install')
