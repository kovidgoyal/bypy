#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os

from virtual_machine.run import shutdown, wait_for_ssh

from .conf import parse_conf_file
from .constants import base_dir
from .utils import single_instance, setup_build_parser
from .vms import Rsync, get_vm_spec


def get_conf():
    ans = getattr(get_conf, 'ans', None)
    if ans is None:
        ans = get_conf.ans = parse_conf_file(
                os.path.join(base_dir(), 'windows.conf'))
    return ans


def singleinstance():
    name = f'bypy-windows-singleinstance-{os.getcwd()}'
    return single_instance(name)


def setup_parser(p):
    p.add_argument('--arch', default='64', choices=('64', '32'), help='The architecture to build for')
    setup_build_parser(p)
    p.set_defaults(func=main)


def main(args):
    vm = get_vm_spec('windows')
    if args.action == 'shutdown':
        shutdown(vm)
        return

    port = wait_for_ssh(vm)
    rsync = Rsync(vm, port)

    output_dir = os.path.join(base_dir(), 'b', 'windows', args.arch, 'dist')
    pkg_dir = os.path.join(base_dir(), 'b', 'windows', args.arch, 'pkg')
    sources_dir = os.path.join(base_dir(), 'b', 'sources-cache')
    os.makedirs(sources_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(pkg_dir, exist_ok=True)

    conf = get_conf()
    win_prefix, python = conf['root'], conf['python']
    perl, ruby = conf.get('perl', 'perl.exe'), conf.get('ruby', 'ruby.exe')
    mesa = conf.get('mesa', 'C:/mesa')
    python2 = conf.get('python2', 'C:/Python27/python.exe')

    drive = win_prefix[0].lower()
    path = win_prefix[2:].replace('\\', '/').replace('//', '/')
    prefix = f'/cygdrive/{drive}{path}'
    win_prefix = win_prefix.replace('/', os.sep)
    cmd = [
        python, os.path.join(win_prefix, 'bypy'),
        f'BYPY_ROOT={win_prefix}', f'BUILD_ARCH={args.arch}',
        f'PYTHON_TWO={python2}', f'PERL={perl}', f'RUBY={ruby}',
        f'MESA={mesa}',
    ]
    if args.action == 'shell':
        if args.send_to_vm:
            rsync.main(sources_dir, pkg_dir, output_dir, cmd, args, prefix=prefix, name=f'sw{args.arch}', only_send=True)
        rsync.run_via_ssh(allocate_tty=True)
        return

    if not singleinstance():
        raise SystemExit(
            'Another instance of the windows container is running')
    rsync.main(sources_dir, pkg_dir, output_dir, cmd, args, prefix=prefix, name=f'sw{args.arch}')
