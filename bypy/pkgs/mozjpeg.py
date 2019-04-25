#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os

from bypy.constants import PREFIX, build_dir, ismacos
from bypy.utils import (install_binaries, iswindows, simple_build,
                        windows_cmake_build, run)


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
        conf = ('--disable-dependency-tracking --disable-shared --with-jpeg8'
                ' --without-turbojpeg')
        if ismacos:
            conf += ' --host x86_64-apple-darwin NASM={}/bin/nasm'.format(
                PREFIX)
        run('autoreconf -fiv')
        simple_build(conf,
                     override_prefix=os.path.join(build_dir(), 'private',
                                                  'mozjpeg'))
