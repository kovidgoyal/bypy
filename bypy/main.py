#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import argparse
import os
import runpy
import shutil
import subprocess
import sys

from .constants import (
    OS_NAME, OUTPUT_DIR, PREFIX, ROOT, SRC, SW, build_dir, islinux
)
from .deps import init_env, main as deps_main
from .utils import mkdtemp, rmtree, run_shell


def option_parser():
    parser = argparse.ArgumentParser(description='Build dependencies')
    a = parser.add_argument
    a('deps', nargs='*', default=[], help='Which dependencies to build')
    a('--shell',
      default=False,
      action='store_true',
      help='Start a shell in the container')
    a('--clean',
      default=False,
      action='store_true',
      help='Remove previously built packages')
    a('--dont-strip',
      default=False,
      action='store_true',
      help='Dont strip the binaries when building')
    a('--compression-level',
      default='9',
      choices=list('123456789'),
      help='Level of compression for the Linux tarball')
    a('--skip-tests',
      default=False,
      action='store_true',
      help='Skip the tests when building')
    a('--sign-installers',
      default=False,
      action='store_true',
      help='Sign the binary installer, needs signing keys in the VMs')
    a('--notarize',
      default=False,
      action='store_true',
      help='Send the app for notarization to the platform vendor')
    a('--no-tty',
      default=False,
      action='store_true',
      help='Assume stdout is not a tty regardless of isatty()')
    a('--build-only',
      help='Build only a single extension module when building'
      ' program, useful for development')
    return parser


def build_program(args):
    init_env()
    init_env_module = runpy.run_path(os.path.join(
        SRC, 'bypy', 'init_env.py'),
        run_name='program')
    os.chdir(SRC)
    ext_dir, bdir = mkdtemp('plugins-'), mkdtemp('build-')
    build_dir(bdir)
    if 'build_c_extensions' in init_env_module:
        extensions_dir = init_env_module['build_c_extensions'](
                ext_dir, args)
        if args.build_only:
            dest = os.path.join(SW, 'dist', 'c-extensions')
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(extensions_dir, dest)
            print('C extensions built in', dest)
            return
    try:
        runpy.run_path(
            os.path.join(SRC, 'bypy', OS_NAME),
            init_globals={
                'args': args,
                'ext_dir': ext_dir,
                'init_env': init_env_module,
            },
            run_name='__main__')
    except Exception:
        import traceback
        traceback.print_exc()
        run_shell()
    finally:
        os.chdir(SRC)
        rmtree(ext_dir), rmtree(bdir)
    if islinux:
        subprocess.run('sudo fstrim --all -v'.split())


def main(args):
    args = option_parser().parse_args(args[2:])
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        if args.shell or args.deps == ['shell']:
            init_env()
            os.chdir(ROOT)
            run_shell(cwd=PREFIX)
            return

        if args.deps == ['program']:
            build_program(args)
        else:
            deps_main(args)
    finally:
        cs = os.path.expanduser('~/code-signing')
        if os.path.exists(cs):
            shutil.rmtree(cs, ignore_errors=True)


if __name__ == '__main__':
    main(sys.argv)
