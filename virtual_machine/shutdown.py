#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import argparse
import os
import subprocess
import socket
from time import monotonic, sleep

from .utils import all_vm_names, base_dir, ssh_port_for_vm, vm_platform


def wait_for_monitor_to_be_removed(path, timeout):
    start = monotonic()
    while os.path.exists(path) and monotonic() - start < timeout:
        sleep(0.1)
    return not os.path.exists(path)


def kill_using_monitor(monitor_path):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(monitor_path)
    sock.sendall(b'quit\n')
    sock.recv(4096)


def shutdown_command(vm_name):
    if vm_platform(vm_name) == 'macos':
        return [
            'osascript', '-e', """'tell app "System Events" to shut down'"""
        ]
    return 'shutdown.exe -s -f -t 0'.split()


def shutdown_one_vm(vm_name, wait_for):
    vm_dir = os.path.join(base_dir, vm_name)
    monitor_path = f'{vm_dir}/monitor.socket'
    if not os.path.exists(monitor_path):
        print(f'{vm_name} is not running')
        return
    port = ssh_port_for_vm(vm_name)
    cmd = shutdown_command(vm_name)
    print(f'Trying a graceful shutdown of {vm_name} with: {cmd}')
    if subprocess.run([
            'ssh', '-p', str(port), 'localhost'] + cmd).returncode == 0:
        if wait_for_monitor_to_be_removed(monitor_path, wait_for):
            return
        print(
            f'Graceful shutdown failed after waiting {wait_for} seconds,'
            ' forcing close')
    else:
        print('Graceful shutdown failed')
    kill_using_monitor(monitor_path)


def main():
    avm = tuple(all_vm_names())
    parser = argparse.ArgumentParser(prog='shutdown',
                                     description='Shutdown Virtual machine')
    parser.add_argument('vm',
                        help='name of the VM to shutdown',
                        choices=avm + ('all',))
    parser.add_argument('--wait-for',
                        type=int,
                        default=20,
                        help='seconds to wait before killing qemu')
    opts = parser.parse_args()
    vms = avm if opts.vm == 'all' else (opts.vm,)
    if len(vms) == 1:
        return shutdown_one_vm(vms[0], opts.wait_for)
    from threading import Thread
    threads = []
    for vm_name in vms:
        t = Thread(target=shutdown_one_vm, args=(vm_name, opts.wait_for))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
