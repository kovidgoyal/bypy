#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import BIN, MAKEOPTS, build_dir, current_build_arch, ismacos, iswindows
from bypy.utils import run, simple_build

needs_lipo = True
# See https://code.qt.io/cgit/qt/qt5.git/tree/coin/provisioning/common/shared/ffmpeg_config_options.txt
common_options = '--disable-programs --disable-doc --disable-debug --enable-network --disable-lzma --enable-pic --disable-vulkan --disable-v4l2-m2m --disable-decoder=truemotion1 --enable-shared --disable-static --enable-gpl'


if iswindows:
    def main(args):
        run('sh', '-c', f'PATH=/usr/bin:$PATH; ./configure --prefix=installed --toolchain=msvc --arch=x86_64 --enable-asm {common_options}')
        run('sh', '-c', f'PATH=/usr/bin:$PATH; make {MAKEOPTS}')
        run('sh', '-c', 'PATH=/usr/bin:$PATH; make install')
        os.rename('installed', os.path.join(build_dir(), 'ffmpeg'))
else:
    def main(args):
        configure_args = [
            f'--prefix={build_dir()}/ffmpeg',
        ] + common_options.split()
        if ismacos:
            configure_args += [
                f'--x86asmexe={BIN}/nasm',
                '--enable-cross-compile', f'--cc=clang -arch {current_build_arch()}', f'--arch={current_build_arch()}',
            ]
        simple_build(configure_args, use_envvars_for_lipo=True)
