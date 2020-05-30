#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shlex

if os.path.exists('/vms'):
    base_dir = os.path.realpath('/vms')
else:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def all_vm_names():
    for x in os.listdir(base_dir):
        if os.path.exists(os.path.join(base_dir, x, 'SystemDisk.qcow2')):
            yield x


def ssh_port_for_vm(name):
    for line in open(os.path.join(base_dir, name, 'machine-spec')):
        line = line.strip()
        if line.startswith('-netdev ') or line.startswith('-nic '):
            return int(line.split(':')[-2].rstrip('-'))
    raise KeyError(f'Failed to find SSH port for {name}')


def vm_platform(name):
    return 'macos' if 'macos' in name.split('-') else 'windows'


def read_build_server():
    try:
        f = open(os.path.expanduser('~/.config/bypy.conf'))
    except FileNotFoundError:
        return 'localhost', [
            'python', os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), 'vm']
    with f:
        server = cmd = None
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            if server is None:
                server = line
                continue
            if cmd is None:
                cmd = shlex.split(line)
                break
        if server is None or cmd is None:
            raise ValueError(
                f'Failed to parse build server config file: {f.name}')
        return server, cmd
