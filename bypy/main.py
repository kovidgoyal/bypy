#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import argparse
import sys

from .utils import run_shell


def option_parser():
    parser = argparse.ArgumentParser(description='Build dependencies')
    a = parser.add_argument
    a('deps', nargs='*', default=[], help='Which dependencies to build')
    a('--shell', default=False, action='store_true',
      help='Start a shell in the container')
    a('--clean', default=False, action='store_true',
      help='Remove previously built packages')
    a('--dont-strip', default=False, action='store_true',
      help='Dont strip the binaries when building')
    a('--compression-level', default='9', choices=list('123456789'),
      help='Level of compression for the Linux tarball')
    a('--skip-tests', default=False, action='store_true',
      help='Skip the tests when building')
    a('--sign-installers', default=False, action='store_true',
      help='Sign the binary installer, needs signing keys in the VMs')
    a('--no-tty', default=False, action='store_true',
      help='Assume stdout is not a tty regardless of isatty()')
    return parser


def main(args):
    args = option_parser().parse_args(args[2:])
    if args.shell or args.deps == ['shell']:
        run_shell()
        return


if __name__ == '__main__':
    main(sys.argv)
