#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys

from virtual_machine.run import shutdown, wait_for_ssh

from .chroot import RECOGNIZED_ARCHES, Chroot
from .constants import base_dir, is64bit
from .utils import setup_build_parser
from .vms import Rsync, get_vm_spec, remote_cmd


def setup_parser(p):
    p.add_argument('--arch', default='64', choices=RECOGNIZED_ARCHES, help='The architecture to build for')
    s = setup_build_parser(p)
    s.add_parser('vm', help='Build the Linux VM automatically')
    p.set_defaults(func=main)


def reexec_as_32bit():
    os.execlp('linux32', 'linux32', sys.executable, os.path.dirname(os.path.dirname(__file__)), *sys.argv[1:])


def main(args):
    vm = get_vm_spec('linux', args.arch)
    chroot = Chroot(args.arch, vm)
    if args.action == 'shutdown':
        if chroot.is_chroot_based:
            print('Shutdown has no effect on chroot based VMs', file=sys.stderr)
            return
        shutdown(vm)
        return
    if chroot.is_chroot_based and args.arch == '32' and is64bit:
        os.environ['BUILD_ARCH'] = args.arch
        reexec_as_32bit()

    output_dir = os.path.join(base_dir(), 'b', 'linux', args.arch, 'dist')
    pkg_dir = os.path.join(base_dir(), 'b', 'linux', args.arch, 'pkg')
    sources_dir = os.path.join(base_dir(), 'b', 'sources-cache')
    os.makedirs(sources_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(pkg_dir, exist_ok=True)

    if args.action == 'vm':
        chroot.build_vm()
        return

    if chroot.is_chroot_based:
        if args.action == 'reconnect':
            raise SystemExit('This is a chroot based VM cannot reconnect to it')
        rsync = Rsync(chroot.vm_path)
        if args.action == 'shell':
            if args.full:
                rsync.to_chroot()
            def run_shell():
                if args.full:
                    from bypy.deps import init_env
                    init_env()
                from bypy.utils import run_shell
                raise SystemExit(run_shell(env=dict(os.environ)))
            chroot.run_func(sources_dir, pkg_dir, output_dir, run_shell)
        if not chroot.single_instance():
            raise SystemExit(f'Another instance of the Linux container {chroot.single_instance_name} is running')
        rsync.to_chroot()
        cmd = remote_cmd(args)
        from .main import global_main
        chroot.run_func(sources_dir, pkg_dir, output_dir, global_main, ['bypy'] + cmd)
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
