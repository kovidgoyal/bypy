#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import argparse
import os
import shlex

from .utils import all_vm_names, base_dir, ssh_port_for_vm


def main():
    parser = argparse.ArgumentParser(prog='run',
                                     description='Run Virtual machine')
    parser.add_argument('vm',
                        help='name of the VM to run',
                        choices=tuple(all_vm_names()))
    parser.add_argument('--gui',
                        action='store_true',
                        help='show the GUI for this virtual machine')
    parser.add_argument('--foreground',
                        action='store_true',
                        help='run in foreground not inside detached screen')

    opts = parser.parse_args()
    vm_dir = os.path.join(base_dir, opts.vm)
    ssh_port = ssh_port_for_vm(opts.vm)
    args = ['qemu-system-x86_64', '-enable-kvm']
    for line in open(os.path.join(vm_dir, 'machine-spec')):
        if line and not line.startswith('#'):
            args.extend(shlex.split(line))
    monitor_path = f'{vm_dir}/monitor.socket'
    if os.path.exists(monitor_path):
        print(f'{opts.vm} is already running,'
              f' SSH into it as: ssh -p {ssh_port} localhost')
        return
    args.extend(['-monitor', f'unix:{monitor_path},server,nowait'])
    args.extend(['-k', 'en-us'])
    if not opts.gui:
        args.append('-nographic')
        if not opts.foreground:
            args = ['screen', '-U', '-d', '-m', '-S', opts.vm] + args
            print(
                f'{opts.vm} started, you can connect to the console with:'
                f' screen -r {opts.vm}')
    os.chdir(vm_dir)
    print(
        f'SSH into {opts.vm} using port: ssh -p {ssh_port} localhost')
    os.execlp(args[0], *args)
