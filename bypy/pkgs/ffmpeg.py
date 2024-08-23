#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import BIN, MAKEOPTS, build_dir, current_build_arch, ismacos, iswindows
from bypy.utils import run, simple_build

needs_lipo = True

if iswindows:
    def main(args):
        run('sh', '-c', 'PATH=/usr/bin:$PATH; ./configure --prefix=installed --toolchain=msvc --enable-shared --disable-static --arch=x86_64 --enable-asm --enable-gpl --disable-programs')
        run('sh', '-c', f'PATH=/usr/bin:$PATH; make {MAKEOPTS}')
        run('sh', '-c', 'PATH=/usr/bin:$PATH; make install')
        os.rename('installed', os.path.join(build_dir(), 'ffmpeg'))
elif ismacos:
    def main(args):
        configure_args = [
            f'--prefix={build_dir()}/ffmpeg',
            '--enable-gpl', '--disable-programs',
            '--enable-shared', '--disable-static',

            '--enable-cross-compile', f'--cc=clang -arch {current_build_arch()}', f'--arch={current_build_arch()}',
            f'--x86asmexe={BIN}/nasm',
        ]
        simple_build(configure_args, use_envvars_for_lipo=True)
