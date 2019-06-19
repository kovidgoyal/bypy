#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import argparse
import os
import runpy
import sys

from .constants import OS_NAME, SRC, build_dir, ROOT, OUTPUT_DIR
from .deps import init_env
from .deps import main as deps_main
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
    a('--no-tty',
      default=False,
      action='store_true',
      help='Assume stdout is not a tty regardless of isatty()')
    return parser


def main(args):
    args = option_parser().parse_args(args[2:])
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.shell or args.deps == ['shell']:
        init_env()
        os.chdir(ROOT)
        run_shell()
        return

    if args.deps == ['program']:
        init_env()
        init_env_module = runpy.run_path(os.path.join(
            SRC, 'bypy', 'init_env.py'),
            run_name='program')
        os.chdir(SRC)
        ext_dir, bdir = mkdtemp('plugins-'), mkdtemp('build-')
        build_dir(bdir)
        if 'build_c_extensions' in init_env_module:
            init_env_module['build_c_extensions'](ext_dir)
        try:
            runpy.run_path(os.path.join(SRC, 'bypy', OS_NAME),
                           init_globals={
                               'args': args,
                               'ext_dir': ext_dir,
                               'init_env': init_env_module
                           },
                           run_name='__main__')
        except Exception:
            import traceback
            traceback.print_exc()
            run_shell()
        finally:
            os.chdir(SRC)
            rmtree(ext_dir), rmtree(bdir)
        return

    deps_main(args)


if __name__ == '__main__':
    main(sys.argv)
