#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import subprocess
import tempfile
from contextlib import suppress

from bypy.deps import install_package


def create_bundle(osname, bitness, dest):
    pkg_dir = os.path.join('bypy', 'b', osname)
    if bitness and osname != 'macos':
        pkg_dir = os.path.join(pkg_dir, bitness)
    pkg_dir = os.path.join(pkg_dir, 'pkg')
    with tempfile.TemporaryDirectory(suffix='.export', dir=pkg_dir) as tdir:
        name = osname
        if bitness:
            name += '-' + bitness
        name += '.tar.xz'
        dest = dest.rstrip('/') + '/'
        print(
            'Installing packages for', osname, bitness, 'from', pkg_dir, '...')
        for x in os.listdir(pkg_dir):
            if '.' not in x:
                install_package(os.path.join(pkg_dir, x), tdir)
        with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tf:
            os.fchmod(tf.fileno(), 0o644)
        print('\tCreating bundle...')
        try:
            subprocess.check_call([
                'tar', '-caf', tf.name] + os.listdir(tdir), cwd=tdir)
            subprocess.check_call(['xz', '-9', '--threads=0', tf.name])
            subprocess.check_call(['scp', tf.name + '.xz', dest + name])
        finally:
            with suppress(FileNotFoundError):
                os.unlink(tf.name)
            with suppress(FileNotFoundError):
                os.unlink(tf.name + '.xz')


def main(args):
    dest = args[-1]
    del args[-1]
    if ':' not in dest:
        raise SystemExit('Usage: export hostname:/path')

    if len(args) > 1:
        which = args[1]
        if which not in ('macos', 'windows', 'linux'):
            raise SystemExit(f'Unknown OS: {which}')
        bitness = '64'
        if len(args) > 2 and args[2] == '32':
            bitness = '32'
        groups = [(which, bitness)]
    else:
        groups = [('macos', '64'), ('linux', '64'), ('windows', '64')]

    for osname, bitness in groups:
        create_bundle(osname, bitness, dest)
