#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import os
import re
import shutil

from .constants import build_dir, PREFIX, MAKEOPTS
from .utils import run, replace_in_file, install_binaries, copy_headers


def main(args):
    # dbus chooses where to look for config files based on values fed to
    # ./configure, so we cannot configure to install it to prefix
    run('./configure --prefix=/usr --sysconfdir=/etc --localstatedir=/var --disable-dependency-tracking --disable-static'
        ' --disable-doxygen-docs --disable-xml-docs --disable-systemd --without-systemdsystemunitdir'
        ' --with-console-auth-dir=/run/console/ --disable-tests')
    run('make ' + MAKEOPTS)
    install_binaries('dbus/.libs/libdbus*.so*')
    os.makedirs(build_dir() + '/lib/pkgconfig')
    shutil.copy2('dbus-1.pc', build_dir() + '/lib/pkgconfig')
    copy_headers('dbus/*.h', destdir='include/dbus-1.0/dbus')
    replace_in_file(os.path.join(build_dir(), 'lib/pkgconfig/dbus-1.pc'), re.compile(br'^prefix=.+$', re.M), b'prefix=%s' % PREFIX)
