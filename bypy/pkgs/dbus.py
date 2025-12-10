#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>


import os

from bypy.constants import PREFIX, build_dir
from bypy.utils import meson_build, replace_in_file


def main(args):
    meson_build(
        apparmor='disabled', doxygen_docs='disabled', qt_help='disabled', relocation='enabled', systemd='disabled', selinux='disabled',
        tools='false', x11_autolaunch='disabled', xml_docs='disabled',
        localstatedir='/var', sharedstatedir='/var/lib',
    )
    replace_in_file(
        os.path.join(build_dir(), 'lib/pkgconfig/dbus-1.pc'),
        'prefix=${pcfiledir}/../..', f'prefix={PREFIX}'
    )
    os.remove(os.path.join(build_dir(), 'libexec/dbus-daemon-launch-helper'))
