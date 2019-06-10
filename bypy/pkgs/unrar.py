#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import ismacos, iswindows
from bypy.utils import (copy_headers, install_binaries, msbuild,
                        replace_in_file, run)


def main(args):
    replace_in_file('dll.cpp', 'WideToChar', 'WideToUtf')
    if iswindows:
        msbuild('UnRARDll.vcxproj')
        install_binaries('./build/*/Release/unrar.dll', 'bin')
        install_binaries('./build/*/Release/UnRAR.lib', 'lib')
        # from bypy.utils import run_shell
        # run_shell()
    else:
        if ismacos:
            replace_in_file('makefile', 'libunrar.so', 'libunrar.dylib')
        run('make -j4 lib CXXFLAGS=-fPIC')
        install_binaries('libunrar.' + ('dylib' if ismacos else 'so'), 'lib')
    copy_headers('*.hpp', destdir='include/unrar')
