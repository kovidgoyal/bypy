#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import ismacos, iswindows, CL, LIB, PATCHES
from bypy.utils import simple_build, run, install_binaries, copy_headers, apply_patch


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
        apply_patch('chmlib-integer-types.patch', level=1)  # needed for aarch64
        # updated config.guess is needed for aarch64
        with open('config.guess', 'wb') as dest, open(os.path.join(PATCHES, 'config.guess'), 'rb') as src:
            dest.write(src.read())
        conf = '--disable-dependency-tracking'
        if ismacos:
            conf += ' --disable-pread --disable-io64'
        simple_build(conf)
