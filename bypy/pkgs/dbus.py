#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shutil

from bypy.constants import MAKEOPTS, PREFIX, build_dir
from bypy.utils import replace_in_file, run, walk


def main(args):
    # dbus chooses where to look for config files based on values fed to
    # ./configure, so we cannot configure to install it to prefix
    run('./configure --prefix=/usr --sysconfdir=/etc --localstatedir=/var'
        ' --disable-dependency-tracking --disable-static'
        ' --disable-doxygen-docs --disable-xml-docs --disable-systemd'
        ' --without-systemdsystemunitdir'
        ' --with-console-auth-dir=/run/console/ --disable-tests --without-x')
    run('make ' + MAKEOPTS)
    run(f'make install', env={'DESTDIR': build_dir()})
    for x in ('include', 'lib'):
        os.rename(
            os.path.join(build_dir(), 'usr', x), os.path.join(build_dir(), x))
    shutil.rmtree(os.path.join(build_dir(), 'usr'))
    for path in walk(build_dir()):
        if path.endswith('.pc'):
            replace_in_file(path, 'prefix=/usr', f'prefix={PREFIX}')
