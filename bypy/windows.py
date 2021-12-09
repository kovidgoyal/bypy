#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys

from virtual_machine.run import shutdown, wait_for_ssh

from .conf import parse_conf_file
from .constants import base_dir
from .utils import single_instance
from .vms import Rsync, from_vm, get_vm_spec, to_vm


def get_conf():
    ans = getattr(get_conf, 'ans', None)
    if ans is None:
        ans = get_conf.ans = parse_conf_file(
                os.path.join(base_dir(), 'windows.conf'))
    return ans


def singleinstance():
    name = f'bypy-windows-singleinstance-{os.getcwd()}'
    return single_instance(name)


def main(args=tuple(sys.argv)):
    if not singleinstance():
        raise SystemExit(
            'Another instance of the windows container is running')
    conf = get_conf()
    win_prefix, python = conf['root'], conf['python']
    perl, ruby = conf.get('perl', 'perl.exe'), conf.get('ruby', 'ruby.exe')
    mesa = conf.get('mesa', 'C:/mesa')
    python2 = conf.get('python2', 'C:/Python27/python.exe')
    vm = get_vm_spec('windows')
    if len(args) > 1:
        if args[1] == 'shutdown':
            shutdown(vm)
            return
    arch = '64'
    if len(args) > 1 and args[1] in ('64', '32'):
        arch = args[1]
        del args[1]
    port = wait_for_ssh(vm)
    rsync = Rsync(vm, port)
    output_dir = os.path.join(base_dir(), 'b', 'windows', arch, 'dist')
    pkg_dir = os.path.join(base_dir(), 'b', 'windows', arch, 'pkg')
    sources_dir = os.path.join(base_dir(), 'b', 'sources-cache')
    os.makedirs(sources_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(pkg_dir, exist_ok=True)

    drive = win_prefix[0].lower()
    path = win_prefix[2:].replace('\\', '/').replace('//', '/')
    prefix = f'/cygdrive/{drive}{path}'
    win_prefix = win_prefix.replace('/', os.sep)
    to_vm(rsync, sources_dir, pkg_dir, prefix=prefix, name=f'sw{arch}')
    cmd = [
        python, os.path.join(win_prefix, 'bypy'), 'main',
        f'BYPY_ROOT={win_prefix}', f'BUILD_ARCH={arch}',
        f'PYTHON_TWO={python2}', f'PERL={perl}', f'RUBY={ruby}',
        f'MESA={mesa}',
    ] + list(args)
    try:
        rsync.run_via_ssh(*cmd, allocate_tty=True)
    finally:
        from_vm(
            rsync, sources_dir, pkg_dir, output_dir,
            prefix=prefix, name=f'sw{arch}')


if __name__ == '__main__':
    main()
