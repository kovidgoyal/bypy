#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import iswindows
from bypy.utils import copy_headers, install_binaries, msbuild, simple_build


needs_lipo = True


def main(args):
    if iswindows:
        msbuild('libiconv.vcxproj')
        copy_headers('include/iconv.h')
        install_binaries('./output/*/Release/libiconv.dll', 'bin')
        install_binaries('./output/*/Release/libiconv.lib', 'lib')
        # from bypy.utils import run_shell
        # run_shell()
    else:
        simple_build(
            '--disable-dependency-tracking --disable-static --enable-shared')


def filter_pkg(parts):
    return 'locale' in parts
