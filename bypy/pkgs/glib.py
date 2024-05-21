#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os

from bypy.constants import BIN, LIBDIR, PREFIX
from bypy.utils import ModifiedEnv, meson_build


def main(args):
    with ModifiedEnv(
            LD_LIBRARY_PATH=LIBDIR,
            PATH=f'{BIN}:' + os.environ['PATH']
    ):
        os.makedirs(
            os.path.join(f'{PREFIX}/lib/dbus-1.0/include'), exist_ok=True)
        meson_build(
            force_posix_threads='true', documentation='false', library_path=True,
            selinux='disabled', c_link_args=f'-L{LIBDIR} -liconv', **{'man-pages': 'disabled'})
