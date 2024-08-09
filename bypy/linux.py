#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os

from virtual_machine.run import shutdown, wait_for_ssh

from .chroot import Chroot, RECOGNIZED_ARCHES
from .constants import base_dir
from .vms import Rsync, get_vm_spec
from .utils import setup_build_parser


def setup_parser(p):
    p.add_argument('--arch', default='64', choices=RECOGNIZED_ARCHES, help='The architecture to build for')
    s = setup_build_parser(p)
    s.add_parser('vm', help='Build the Linux VM automatically')
    p.set_defaults(func=main)


def main(args):
    vm = get_vm_spec('linux', args.arch)
    if args.action == 'shutdown':
        shutdown(vm)
        return
    chroot = Chroot(args.arch)
    output_dir = os.path.join(base_dir(), 'b', 'linux', args.arch, 'dist')
    pkg_dir = os.path.join(base_dir(), 'b', 'linux', args.arch, 'pkg')
    sources_dir = os.path.join(base_dir(), 'b', 'sources-cache')
    os.makedirs(sources_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(pkg_dir, exist_ok=True)

    if args.action == 'vm':
        chroot.build_vm()
        return

    ba = f'linux-{args.arch}'
    cmd = ['python3', os.path.join('/', 'bypy'), f'BYPY_ARCH={ba}']
    port = wait_for_ssh(vm)
    rsync = Rsync(vm, port)

    if args.arch == 'arm64':
        # for some reason automounting does not always work in the Ubuntu Jammy ARM VM.
        rsync.run_via_ssh('sudo', 'mount', '-a', raise_exception=False)

    if args.action == 'shell':
        return rsync.run_shell(sources_dir, pkg_dir, output_dir, cmd, ba, args)
    if args.action == 'reconnect':
        return rsync.reconnect(sources_dir, pkg_dir, output_dir, cmd, ba, args)

    if not chroot.single_instance():
        raise SystemExit(f'Another instance of the Linux container {chroot.single_instance_name} is running')

    rsync.main(sources_dir, pkg_dir, output_dir, cmd, args)
