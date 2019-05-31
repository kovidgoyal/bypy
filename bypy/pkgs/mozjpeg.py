#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import re

from bypy.constants import BIN, build_dir, ismacos
from bypy.utils import (ModifiedEnv, install_binaries, iswindows, run,
                        simple_build, windows_cmake_build, replace_in_file)


def main(args):
    if iswindows:
        windows_cmake_build()
        install_binaries('build/jpegtran-static.exe',
                         'bin',
                         fname_map=lambda x: 'jpegtran-calibre.exe')
        install_binaries('build/cjpeg-static.exe',
                         'bin',
                         fname_map=lambda x: 'cjpeg-calibre.exe')
    else:
        env = {}
        if ismacos:
            env['PATH'] = BIN + os.pathsep + os.environ['PATH']
            env['LIBTOOLIZE'] = 'glibtoolize'
            env['LIBTOOL'] = 'glibtool'
        with ModifiedEnv(**env):
            run('autoreconf -fiv')
        conf = ('--disable-dependency-tracking --disable-shared --with-jpeg8'
                ' --without-turbojpeg')
        env = {}
        if ismacos:
            conf += f' --host x86_64-apple-darwin NASM={BIN}/nasm'
            replace_in_file('configure', re.compile(
                br'^PKG_CHECK_MODULES.libpng.+?\bfi\b', re.M | re.DOTALL),
                'HAVE_LIBPNG=1\nHAVE_LIBPNG_TRUE="#"\n')
        simple_build(conf,
                     override_prefix=os.path.join(build_dir(), 'private',
                                                  'mozjpeg'))
