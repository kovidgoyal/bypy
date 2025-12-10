#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.constants import PKG_CONFIG_PATH, build_dir
from bypy.utils import simple_build, ModifiedEnv


def main(args):
    # make install tries to write to $HOME/.terminfo
    with ModifiedEnv(HOME=build_dir()):
        simple_build(
            '--with-shared --without-debug --without-ada --enable-widec'
            ' --with-normal --enable-pc-files --disable-db-install --without-manpages'
            f' --with-pkg-config-libdir={PKG_CONFIG_PATH}'
            # without the following ncurses will look in the BUILD_DIR
            # for terminfo files even on target systems. Instead use
            # a bunch of common locations.
            ' --with-terminfo-dirs=/usr/share/terminfo:/etc/terminfo:'
            '/lib/terminfo:/usr/lib/terminfo'
            ' --with-default-terminfo-dir=/usr/share/terminfo',
        )


def filter_pkg(parts):
    return (
        'terminfo' in parts or 'tabset' in parts or 'bin' in parts or
        '.terminfo' in parts
    )
