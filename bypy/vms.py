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
from .utils import cmdline_for_dependencies, cmdline_for_program


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


def remote_cmd(args):
    if args.action == 'dependencies':
        return cmdline_for_dependencies(args)
    return cmdline_for_program(args)


class Rsync(object):

    excludes = frozenset({
        '*.pyc', '*.pyo', '*.swp', '*.swo', '*.pyj-cached', '*~', '.git'})

    def __init__(self, spec, port, rsync_cmd=''):
        self.server = server_from_spec(spec)
        self.remote_rsync_cmd = rsync_cmd
        self.port = port

    def run_via_ssh(self, *args, allocate_tty=False, raise_exception=True):
        cmd = ssh_command_to(*args, server=self.server, port=self.port, allocate_tty=allocate_tty)
        if raise_exception:
            subprocess.check_call(cmd)
        else:
            return subprocess.run(cmd)

    def main(self, sources_dir, pkg_dir, output_dir, cmd_prefix, args, prefix='/', name='sw', only_send=False):
        ws_cmd = list(cmd_prefix) + ['worker-status']
        to_vm(self, ws_cmd, sources_dir, pkg_dir, prefix=prefix, name=name)
        if only_send:
            return
        cp = self.run_via_ssh(*cmd_prefix, *remote_cmd(args), allocate_tty=True, raise_exception=False)
        from_vm(self, sources_dir, pkg_dir, output_dir, prefix=prefix, name=name)
        raise SystemExit(cp.returncode)

    def from_vm(self, from_, to, excludes=frozenset()):
        f = self.server + ':' + from_
        return self.rsync_command(f, to, excludes)

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
            'rsync', '-a', '-zz', '-e', ssh, '--delete', '--delete-excluded', '--chmod', 'og-w',
        ]
        if self.remote_rsync_cmd:
            cmd += ['--rsync-path', self.remote_rsync_cmd]
        return cmd + [from_ + '/', to]


def run_sync_jobs(cmds, retry=False):
    while True:
        workers = [
            (cmd, subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT))
            for cmd in cmds
        ]
        for (cmd, w) in workers:
            w.wait()
        failures = []
        for (cmd, w) in workers:
            if w.returncode != 0:
                failures.append((cmd, w.stdout.read()))
        if failures:
            for (cmd, w) in failures:
                print(f'The command {cmd} failed')
                sys.stderr.buffer.write(w)
            if retry:
                q = input('Would you like to retry downloading data from the VM? [y/n] ')
                if q == 'y':
                    continue
            raise SystemExit(1)
        else:
            break


def to_vm(rsync, initial_cmd, sources_dir, pkg_dir, prefix='/', name='sw'):
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
    initial_cmd += dirs_to_ensure
    cp = rsync.run_via_ssh(*initial_cmd, raise_exception=False)
    if cp.returncode == 0:
        run_sync_jobs(to_vm_calls)
        print(f'Mirroring took {time.monotonic() - start:.1f} seconds', flush=True)
    elif cp.returncode in (1, 2):
        # initial creation when bypy is not present or outdated in the VM
        print('Running initial cmd to sync data to VM failed', initial_cmd, file=sys.stderr, flush=True)
        rsync.run_via_ssh('mkdir', '-p', *dirs_to_ensure)
        run_sync_jobs(to_vm_calls)
        print(f'Mirroring took {time.monotonic() - start:.1f} seconds', flush=True)
    elif cp.returncode == 13:
        print('\x1b[31mThere is an existing job running, reconnecting to that job...\x1b[m', flush=True)


def from_vm(rsync, sources_dir, pkg_dir, output_dir, prefix='/', name='sw'):
    start = time.monotonic()
    print('Mirroring data from VM...', flush=True)
    prefix = prefix.rstrip('/') + '/'
    cmds = []
    a = cmds.append
    a(rsync.from_vm(prefix + name + '/dist', output_dir))
    a(rsync.from_vm(prefix + 'sources', sources_dir))
    a(rsync.from_vm(prefix + name + '/pkg', pkg_dir))
    run_sync_jobs(cmds, retry=True)
    print(f'Mirroring took {time.monotonic() - start:.1f} seconds', flush=True)
