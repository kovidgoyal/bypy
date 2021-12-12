#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import shlex
import subprocess
import sys
import time

from virtual_machine.run import server_from_spec, ssh_command_to

from .conf import parse_conf_file
from .constants import base_dir


def get_rsync_conf():
    ans = getattr(get_rsync_conf, 'ans', None)
    if ans is None:
        ans = get_rsync_conf.ans = parse_conf_file(
                os.path.join(base_dir(), 'rsync.conf'))
    return ans


def get_vm_spec(system, arch=''):
    ans = os.path.join(base_dir(), 'b', system, arch, 'vm')
    conf = os.path.join(base_dir(), 'virtual-machines.conf')
    if os.path.exists(conf):
        key = system
        if arch:
            key += '_' + arch
        vms = parse_conf_file(conf)
        ans = vms.get(key, ans)
    return ans


class Rsync(object):

    excludes = frozenset({
        '*.pyc', '*.pyo', '*.swp', '*.swo', '*.pyj-cached', '*~', '.git'})

    def __init__(self, spec, port):
        self.server = server_from_spec(spec)
        self.port = port

    def run_via_ssh(self, *args, allocate_tty=False, raise_exception=True):
        cmd = ssh_command_to(*args, server=self.server, port=self.port, allocate_tty=allocate_tty)
        if raise_exception:
            subprocess.check_call(cmd)
        else:
            return subprocess.run(cmd)

    def main(self, sources_dir, pkg_dir, output_dir, cmd_prefix, args, prefix='/', name='sw'):
        cp = self.run_via_ssh(*cmd_prefix, args[0], 'bypy-worker-status', raise_exception=False)
        if cp.returncode == 1:
            print('An existing job is running, reconnecting to that job...', flush=True)
        else:
            to_vm(self, sources_dir, pkg_dir, prefix=prefix, name=name)
        cp = self.run_via_ssh(*cmd_prefix, *args, allocate_tty=True, raise_exception=False)
        while True:
            try:
                from_vm(self, sources_dir, pkg_dir, output_dir, prefix=prefix, name=name)
                break
            except Exception as e:
                print(f'Downloading data from VM failed: {e}', file=sys.stderr)
                ans = input('Would you like to try downloading again [y/n]? ')
                if ans.lower() not in ('', 'y'):
                    break
        raise SystemExit(cp.returncode)

    def from_vm(self, from_, to, excludes=frozenset()):
        f = self.server + ':' + from_
        return self.rsync_command(f, to, excludes)

    def ensure_remote_dirs(self, *dirs):
        if dirs:
            self.run_via_ssh('mkdir', '-p', *dirs)

    def to_vm(self, from_, to, excludes=frozenset()):
        t = self.server + ':' + to
        return self.rsync_command(from_, t, excludes)

    def rsync_command(self, from_, to, excludes=frozenset()):
        ssh = shlex.join(ssh_command_to(server=self.server, port=self.port)[:-1])
        if isinstance(excludes, type('')):
            excludes = excludes.split()
        excludes = frozenset(excludes) | self.excludes
        excludes = ['--exclude=' + x for x in excludes]
        cmd = [
            'rsync', '-a', '-zz', '-e', ssh, '--delete', '--delete-excluded'
        ] + excludes + [from_ + '/', to]
        return cmd


def run_sync_jobs(cmds):
    workers = [
        (cmd, subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT))
        for cmd in cmds
    ]
    for (cmd, w) in workers:
        w.wait()
    for (cmd, w) in workers:
        if w.returncode != 0:
            print(f'The command {cmd} failed')
            sys.stderr.buffer.write(w.stdout.read())
            raise SystemExit(w.returncode)


def to_vm(rsync, sources_dir, pkg_dir, prefix='/', name='sw'):
    start = time.monotonic()
    print('Mirroring data to the VM...', flush=True)
    prefix = prefix.rstrip('/') + '/'
    src_dir = os.path.dirname(base_dir())
    dirs_to_ensure = []
    to_vm_calls = []

    def a(src, to, excludes=frozenset()):
        dirs_to_ensure.append(to)
        to_vm_calls.append(rsync.to_vm(src, to, excludes))

    if os.path.exists(os.path.join(src_dir, 'setup.py')):
        excludes = get_rsync_conf()['to_vm_excludes']
        a(src_dir, prefix + 'src', '/bypy/b ' + excludes)

    base = os.path.dirname(os.path.abspath(__file__))
    a(os.path.dirname(base), prefix + 'bypy')
    a(sources_dir, prefix + 'sources')
    a(pkg_dir, prefix + name + '/pkg')
    if 'PENV' in os.environ:
        code_signing = os.path.expanduser(os.path.join(
            os.environ['PENV'], 'code-signing'))
        if os.path.exists(code_signing):
            a(code_signing, '~/code-signing')
    rsync.ensure_remote_dirs(*dirs_to_ensure)
    run_sync_jobs(to_vm_calls)
    print(f'Mirroring took {time.monotonic() - start:.1f} seconds', flush=True)


def from_vm(rsync, sources_dir, pkg_dir, output_dir, prefix='/', name='sw'):
    start = time.monotonic()
    print('Mirroring data from VM...', flush=True)
    prefix = prefix.rstrip('/') + '/'
    cmds = []
    a = cmds.append
    a(rsync.from_vm(prefix + name + '/dist', output_dir))
    a(rsync.from_vm(prefix + 'sources', sources_dir))
    a(rsync.from_vm(prefix + name + '/pkg', pkg_dir))
    run_sync_jobs(cmds)
    print(f'Mirroring took {time.monotonic() - start:.1f} seconds', flush=True)
