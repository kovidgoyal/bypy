#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os

from .constants import isosx, iswindows
from .utils import simple_build, run, install_binaries, copy_headers


def main(args):
    if iswindows:
        os.chdir('src')
        for f in 'chm_lib.c lzx.c'.split():
            run('cl.exe /c /nologo /MD /W3 /DWIN32 -c ' + f)
        run('lib.exe -nologo chm_lib.obj lzx.obj -OUT:chmlib.lib')
        install_binaries('chmlib.lib')
        copy_headers('chm_lib.h')
    else:
        conf = '--disable-dependency-tracking'
        if isosx:
            conf += ' --disable-pread --disable-io64'
        simple_build(conf)
