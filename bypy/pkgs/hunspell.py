#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import BIN, ismacos
from bypy.utils import (ModifiedEnv, copy_headers, current_dir,
                        install_binaries, iswindows, msbuild, run,
                        simple_build)


def main(args):
    if iswindows:
        with current_dir('msvc'):
            msbuild('Hunspell.sln', configuration='Release_dll')
            install_binaries('./*/Release_dll/libhunspell.dll', 'bin')
            install_binaries('./*/Release_dll/libhunspell.lib', 'lib')
        # from bypy.utils import run_shell
        # run_shell()
        copy_headers('src/hunspell/*.hxx', destdir='include/hunspell')
        copy_headers('src/hunspell/*.h', destdir='include/hunspell')
        copy_headers('msvc/*.h', destdir='include/hunspell')
    else:
        env = {}
        if ismacos:
            env['PATH'] = BIN + os.pathsep + os.environ['PATH']
            env['LIBTOOLIZE'] = 'glibtoolize'
            env['LIBTOOL'] = 'glibtool'
        with ModifiedEnv(**env):
            run('autoreconf -fiv')
        conf = '--disable-dependency-tracking'
        env = {}
        if ismacos:
            conf += ' --host x86_64-apple-darwin'
        simple_build(conf)
