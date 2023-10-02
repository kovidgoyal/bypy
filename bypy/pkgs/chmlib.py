#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import ismacos, iswindows, CL, LIB, PATCHES, is_cross_half_of_lipo_build
from bypy.utils import simple_build, run, install_binaries, copy_headers, apply_patch, replace_in_file


needs_lipo = True


def main(args):
    apply_patch('chmlib-empty-file-not-dir.patch', level=1)  # needed for aarch64
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
        # test for malloc breaks on macos universal.
        # All system we care about have malloc anyway
        replace_in_file(
            'configure',
            'if test $ac_cv_func_malloc_0_nonnull = yes; then',
            'if test 1; then'
        )
        replace_in_file('src/chm_lib.c', 'pread64', 'pread')
        apply_patch('chmlib-integer-types.patch', level=1)  # needed for aarch64
        # updated config.guess is needed for aarch64
        with open('config.guess', 'wb') as dest, open(os.path.join(PATCHES, 'config.guess'), 'rb') as src:
            dest.write(src.read())
        if ismacos and is_cross_half_of_lipo_build():
            with open('config.sub', 'w') as dest:
                dest.write('echo arm-apple-darwin')
        conf = '--disable-dependency-tracking'
        if ismacos:
            conf += ' --disable-pread --disable-io64'
        simple_build(conf)
