#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shutil

from bypy.constants import build_dir, MAKEOPTS, PREFIX
from bypy.utils import run, install_binaries, copy_headers, replace_in_file


def main(args):
    # dbus chooses where to look for config files based on values fed to
    # ./configure, so we cannot configure to install it to prefix
    run('./configure --prefix=/usr --sysconfdir=/etc --localstatedir=/var --disable-dependency-tracking --disable-static'
        ' --disable-doxygen-docs --disable-xml-docs --disable-systemd --without-systemdsystemunitdir'
        ' --with-console-auth-dir=/run/console/ --disable-tests')
    run('make ' + MAKEOPTS)
    install_binaries('dbus/.libs/libdbus*.so*')
    os.makedirs(build_dir() + '/lib/pkgconfig')
    replace_in_file('dbus-1.pc', 'prefix=${original_prefix}', f'prefix={PREFIX}')
    shutil.copy2('dbus-1.pc', build_dir() + '/lib/pkgconfig')
    copy_headers('dbus/*.h', destdir='include/dbus-1.0/dbus')
