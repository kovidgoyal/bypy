#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import CFLAGS, UNIVERSAL_ARCHES, ismacos, iswindows
from bypy.utils import copy_headers, simple_build


def main(args):
    if iswindows:
        # On windows we dont actually build sqlite as the python build script
        # downloads its own version locked sqlite. We just install the headers
        copy_headers('sqlite3*.h')
        return
    configure = '--disable-dependency-tracking --disable-static'.split()
    if ismacos:
        configure.append(f'CFLAGS={CFLAGS} -O2 -DSQLITE_ENABLE_LOCKING_STYLE')
        if len(UNIVERSAL_ARCHES) > 1:
            configure.append(
                'CC=' + 'clang ' + ' '.join(
                    f'-arch {x}' for x in UNIVERSAL_ARCHES))
            configure.append('CPP=clang -E')
    simple_build(configure)
