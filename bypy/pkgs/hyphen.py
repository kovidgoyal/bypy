#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import CL, LIB, iswindows
from bypy.utils import run, install_binaries, copy_headers, simple_build


needs_lipo = True


def main(args):
    if iswindows:
        for f in 'hnjalloc.c hyphen.c'.split():
            run(f'"{CL}" /c /nologo /MD /W3 /DWIN32 -c ' + f)
        run(f'"{LIB}" -nologo hnjalloc.obj hyphen.obj -OUT:hyphen.lib')
        install_binaries('hyphen.lib')
        copy_headers('hyphen.h')
        return
    simple_build(
        ('--disable-static',), make_args=('install-libLTLIBRARIES', 'install-includeHEADERS'),
        do_install=False, use_envvars_for_lipo=True,
    )
