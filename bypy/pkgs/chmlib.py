#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import ismacos, iswindows, CL, LIB
from bypy.utils import simple_build, run, install_binaries, copy_headers


def main(args):
    if iswindows:
        os.chdir('src')
        for f in 'chm_lib.c lzx.c'.split():
            copy_headers(f, 'src')
            run(f'"{CL}" /c /nologo /MD /W3 /DWIN32 -c ' + f)
        run(f'"{LIB}" -nologo chm_lib.obj lzx.obj -OUT:chmlib.lib')
        install_binaries('chmlib.lib')
        copy_headers('chm_lib.h')
        copy_headers('lzx.h', 'src')
    else:
        conf = '--disable-dependency-tracking'
        if ismacos:
            conf += ' --disable-pread --disable-io64'
        simple_build(conf)
