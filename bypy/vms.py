#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shlex
import socket
import subprocess
import tempfile
from time import monotonic, sleep

from .conf import parse_conf_file
from .constants import base_dir


def get_rsync_conf():
    ans = getattr(get_rsync_conf, 'ans', None)
    if ans is None:
        ans = get_rsync_conf.ans = parse_conf_file(
                os.path.join(base_dir(), 'rsync.conf'))
    return ans


def is_host_reachable(name, timeout=1):
    try:
        socket.create_connection((name, 22), timeout).close()
        return True
    except Exception:
        return False


def is_vm_running(name):
    qname = '"%s"' % name
    try:
        lines = subprocess.check_output(
            'VBoxManage list runningvms'.split()).decode('utf-8').splitlines()
    except Exception:
        sleep(1)
        lines = subprocess.check_output(
            'VBoxManage list runningvms'.split()).decode('utf-8').splitlines()
    for line in lines:
        if line.startswith(qname):
            return True
    return False


SSH = [
    'ssh', '-o', 'User=kovid',
    '-o', 'ControlMaster=auto', '-o', 'ControlPersist=yes',
    '-o', 'ControlPath={}/%r@%h:%p'.format(tempfile.gettempdir())
]


def run_in_vm(name, *args, **kw):
    if len(args) == 1:
        args = shlex.split(args[0])
    p = subprocess.Popen(SSH + ['-t', name] + list(args))
    if kw.get('is_async'):
        return p
    if p.wait() != 0:
        raise SystemExit(p.wait())


def ensure_vm(name):
    if not is_vm_running(name):
        subprocess.Popen(['VBoxHeadless', '--startvm', name])
        sleep(2)
    print('Waiting for SSH server to start...')
    st = monotonic()
    while not is_host_reachable(name):
        sleep(0.1)
    print('SSH server started in', '%.1f' % (monotonic() - st), 'seconds')


def shutdown_vm(name, max_wait=15):
    start_time = monotonic()
    if not is_vm_running(name):
        return
    isosx = name.startswith('osx-')
    cmd = 'sudo shutdown -h now' if isosx else 'shutdown.exe -s -f -t 0'
    shp = run_in_vm(name, cmd, is_async=True)
    shutdown_time = monotonic()

    try:
        while is_host_reachable(name) and monotonic() - start_time <= max_wait:
            sleep(0.1)
        subprocess.Popen(SSH + ['-O', 'exit', name])
        if is_host_reachable(name):
            wait = '%.1f' % (monotonic() - start_time)
            print(f'Timed out waiting for {name} to shutdown'
                  f' cleanly after {wait} seconds, forcing shutdown')
            subprocess.check_call(
                ('VBoxManage controlvm %s poweroff' % name).split())
            return
        print('SSH server shutdown, now waiting for VM to poweroff...')
        if isosx:
            # OS X VM hangs on shutdown, so just give it at most 5 seconds to
            # shutdown cleanly.
            max_wait = 5 + shutdown_time - start_time
        while is_vm_running(name) and monotonic() - start_time <= max_wait:
            sleep(0.1)
        if is_vm_running(name):
            wait = '%.1f' % (monotonic() - start_time)
            print(f'Timed out waiting for {name} to shutdown'
                  f' cleanly after {wait} seconds, forcing shutdown')
            subprocess.check_call(
                ('VBoxManage controlvm %s poweroff' % name).split())
    finally:
        if shp.poll() is None:
            shp.kill()


class Rsync(object):

    excludes = frozenset({
        '*.pyc', '*.pyo', '*.swp', '*.swo', '*.pyj-cached', '*~', '.git'})

    def __init__(self, name):
        self.name = name

    def from_vm(self, from_, to, excludes=frozenset()):
        f = self.name + ':' + from_
        self(f, to, excludes)

    def to_vm(self, from_, to, excludes=frozenset()):
        t = self.name + ':' + to
        self(from_, t, excludes)

    def __call__(self, from_, to, excludes=frozenset()):
        ssh = ' '.join(SSH)
        if isinstance(excludes, type('')):
            excludes = excludes.split()
        excludes = frozenset(excludes) | self.excludes
        excludes = ['--exclude=' + x for x in excludes]
        cmd = [
            'rsync', '-a', '-e', ssh, '--delete', '--delete-excluded'
        ] + excludes + [from_ + '/', to]
        # print(' '.join(cmd))
        print('Syncing', from_)
        p = subprocess.Popen(cmd)
        if p.wait() != 0:
            raise SystemExit(p.wait())


def to_vm(rsync, sources_dir, pkg_dir, prefix='/', name='sw'):
    print('Mirroring data to the VM...')
    prefix = prefix.rstrip('/') + '/'
    src_dir = os.path.dirname(base_dir())
    if os.path.exists(os.path.join(src_dir, 'setup.py')):
        excludes = get_rsync_conf()['to_vm_excludes']
        rsync.to_vm(src_dir, prefix + 'src', '/bypy/b ' + excludes)

    base = os.path.dirname(os.path.abspath(__file__))
    rsync.to_vm(os.path.dirname(base), prefix + 'bypy')
    rsync.to_vm(sources_dir, prefix + 'sources')
    rsync.to_vm(pkg_dir, prefix + name + '/pkg')


def from_vm(rsync, sources_dir, pkg_dir, output_dir, prefix='/', name='sw'):
    print('Mirroring data from VM...')
    prefix = prefix.rstrip('/') + '/'
    rsync.from_vm(prefix + name + '/dist', output_dir)
    rsync.from_vm(prefix + 'sources', sources_dir)
    rsync.from_vm(prefix + name + '/pkg', pkg_dir)


def run_main(name, *cmd):
    run_in_vm(name, *cmd)
