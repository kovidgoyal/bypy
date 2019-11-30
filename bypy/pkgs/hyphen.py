#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import CL, LIB, build_dir, iswindows
from bypy.utils import run, install_binaries, copy_headers


def main(args):
    if iswindows:
        for f in 'hnjalloc.c hyphen.c'.split():
            run(f'"{CL}" /c /nologo /MD /W3 /DWIN32 -c ' + f)
        run(f'"{LIB}" -nologo hnjalloc.obj hyphen.obj -OUT:hyphen.lib')
        install_binaries('hyphen.lib')
        copy_headers('hyphen.h')
        return
    run('./configure', f'--prefix={build_dir()}', '--disable-static')
    run('make', 'install-libLTLIBRARIES')
    run('make', 'install-includeHEADERS')
