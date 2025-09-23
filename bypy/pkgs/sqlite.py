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
    CPPFLAGS="\
-DSQLITE_ENABLE_FTS5 \
-DSQLITE_ENABLE_FTS4 \
-DSQLITE_ENABLE_FTS3 \
-DSQLITE_ENABLE_FTS3_PARENTHESIS \
-DSQLITE_ENABLE_JSON1 \
-DSQLITE_ENABLE_RTREE \
-DSQLITE_ENABLE_GEOPOLY \
-DSQLITE_ENABLE_DBSTAT_VTAB \
-DSQLITE_ENABLE_CSV \
-DSQLITE_ENABLE_SERIES \
-DSQLITE_ENABLE_CARRAY \
-DSQLITE_ENABLE_PREUPDATE_HOOK \
-DSQLITE_ENABLE_SESSION \
-DSQLITE_ENABLE_MATH_FUNCTIONS \
-DSQLITE_ENABLE_STAT4 \
-DSQLITE_ENABLE_SHA3 \
-DSQLITE_ENABLE_UUID \
-DSQLITE_ENABLE_SOUNDEX \
-DSQLITE_ENABLE_UPDATE_DELETE_LIMIT \
-DSQLITE_ENABLE_OFFSET_SQL_FUNC \
-DSQLITE_ENABLE_FILEIO \
-DSQLITE_ENABLE_REGEXP \
-DSQLITE_ENABLE_COLUMN_METADATA"
    simple_build(configure, env={'CPPFLAGS': CPPFLAGS})
