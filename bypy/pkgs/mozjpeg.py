#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os

from .constants import build_dir, isosx, PREFIX
from .utils import simple_build, windows_cmake_build, iswindows, install_binaries


def main(args):
    if iswindows:
        windows_cmake_build()
        install_binaries('build/jpegtran-static.exe', 'bin', fname_map=lambda x: 'jpegtran-calibre.exe')
        install_binaries('build/cjpeg-static.exe', 'bin', fname_map=lambda x: 'cjpeg-calibre.exe')
    else:
        conf = '--disable-dependency-tracking --disable-shared --with-jpeg8 --without-turbojpeg'
        if isosx:
            conf += ' --host x86_64-apple-darwin NASM={}/bin/nasm'.format(PREFIX)
        simple_build(conf, override_prefix=os.path.join(build_dir(), 'private', 'mozjpeg'))
