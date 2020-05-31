#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import argparse
import os
import json

from .utils import all_vm_names, base_dir, ssh_port_for_vm, vm_platform


def vm_status(name):
    vm_dir = os.path.join(base_dir, name)
    monitor_path = f'{vm_dir}/monitor.socket'
    sz = os.path.getsize(f'{vm_dir}/SystemDisk.qcow2')
    return {
        'running': os.path.exists(monitor_path),
        'ssh_port': ssh_port_for_vm(name),
        'platform': vm_platform(name),
        'size_of_disk_file_gb': sz / (1024**3),
    }


def main():
    avm = tuple(all_vm_names())
    parser = argparse.ArgumentParser(
        prog='status', description='Get status of Virtual machine')
    parser.add_argument('vm', help='name of the VM', choices=avm)
    opts = parser.parse_args()
    print(json.dumps(vm_status(opts.vm), indent=2))
