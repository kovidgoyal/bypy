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


def setup_parser(p):
    p.add_argument('dest', help='The destination, for example: hostname:/path')
    p.add_argument('which_os', choices=('macos', 'linux', 'windows'), help='Which OS to build for')
    p.add_argument('--arch', default='64', choices=('64', '32', 'arm64'), help='The CPU architecture')
    p.set_defaults(func=main)


def main(args):
    dest = args.dest
    if ':' not in dest:
        raise SystemExit('Usage: export hostname:/path')

    create_bundle(args.which_os, args.arch, dest)
