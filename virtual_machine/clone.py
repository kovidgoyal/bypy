#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import argparse
import os

from .utils import all_vm_names, base_dir


def main():
    avm = tuple(all_vm_names())
    parser = argparse.ArgumentParser(
        prog='clone',
        description='Clone the specified VM from this machine to a'
        ' remote one, copying only changed blocks')
    parser.add_argument('vm', help='name of the VM to clone', choices=avm)
    parser.add_argument('dest',
                        default='vm@dl1:/vms',
                        nargs='?',
                        help='The remote server to clone the machine to')
    opts = parser.parse_args()
    vm_name = opts.vm
    vm_dir = os.path.join(base_dir, vm_name)
    os.execlp('rsync', 'rsync', '-rv', '-zz', '--inplace', '--no-whole-file',
              '--progress', vm_dir, opts.dest)
