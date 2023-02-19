#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import ismacos, iswindows
from bypy.utils import (
    copy_headers, current_build_arch, install_binaries,
    is_arm_half_of_lipo_build, msbuild, replace_in_file, run
)

needs_lipo = True


def main(args):
    replace_in_file('dll.cpp', 'WideToChar', 'WideToUtf')
    if iswindows:
        # see https://github.com/microsoft/vcpkg/pull/8053
        replace_in_file(
            'UnRARDll.vcxproj',
            '<StructMemberAlignment>4Bytes</StructMemberAlignment>', '')
        msbuild('UnRARDll.vcxproj')
        install_binaries('./build/*/Release/unrar.dll', 'bin')
        install_binaries('./build/*/Release/UnRAR.lib', 'lib')
        # from bypy.utils import run_shell
        # run_shell()
    else:
        flags = '-fPIC'
        if ismacos:
            replace_in_file('makefile', 'libunrar.so', 'libunrar.dylib')
            if is_arm_half_of_lipo_build():
                flags += f' -arch {current_build_arch()}'
            replace_in_file('makefile', 'LDFLAGS=', f'LDFLAGS=-arch {current_build_arch()} ')
        replace_in_file('makefile', 'CXXFLAGS=', f'CXXFLAGS={flags} ')
        run('make -j4 lib')
        install_binaries('libunrar.' + ('dylib' if ismacos else 'so'), 'lib')
    copy_headers('*.hpp', destdir='include/unrar')
