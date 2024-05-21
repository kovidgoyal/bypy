#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import meson_build


def main(args):
    meson_build(**{
        'enable-wayland': 'false',
        'xkb-config-root': '/usr/share/X11/xkb',
        'xkb-config-extra-path': '/etc/xkb',
        'x-locale-root': '/usr/share/X11/locale',
        'bash-completion-path': '/tmp',
        'enable-docs': 'false',
    })
