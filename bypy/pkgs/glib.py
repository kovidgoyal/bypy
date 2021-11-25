#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
from bypy.constants import LIBDIR, PREFIX
from bypy.utils import meson_build, ModifiedEnv


def main(args):
    with ModifiedEnv(
            LD_LIBRARY_PATH=LIBDIR,
            PATH=f'{PREFIX}/bin:' + os.environ['PATH']
    ):
        os.makedirs(
            os.path.join(f'{PREFIX}/lib/dbus-1.0/include'), exist_ok=True)
        meson_build(
            force_posix_threads='true', gtk_doc='false',
            man='false', selinux='disabled', iconv='external')
