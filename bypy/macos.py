#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys

from .conf import parse_conf_file
from .constants import base_dir
from .utils import single_instance
from .vms import Rsync, ensure_vm, from_vm, run_main, shutdown_vm, to_vm


def get_conf():
    ans = getattr(get_conf, 'ans', None)
    if ans is None:
        ans = get_conf.ans = parse_conf_file(
                os.path.join(base_dir(), 'macos.conf'))
    return ans


def singleinstance():
    name = f'bypy-macos-singleinstance-{os.getcwd()}'
    return single_instance(name)


def main(args=tuple(sys.argv)):
    if not singleinstance():
        raise SystemExit('Another instance of the macOS container is running')
    conf = get_conf()
    vm, prefix, python = conf['vm_name'], conf['root'], conf['python']
    targets = conf.get('targets', '')
    if len(args) > 1:
        if args[1] == 'shutdown':
            shutdown_vm(vm)
            return
    ensure_vm(vm)
    rsync = Rsync(vm)
    output_dir = os.path.join(base_dir(), 'b', 'macos', 'dist')
    pkg_dir = os.path.join(base_dir(), 'b', 'macos', 'pkg')
    sources_dir = os.path.join(base_dir(), 'b', 'sources-cache')
    os.makedirs(sources_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(pkg_dir, exist_ok=True)

    to_vm(rsync, sources_dir, pkg_dir, prefix=prefix)
    cmd = [
        python, os.path.join(prefix, 'bypy'), 'main',
        f'BYPY_ROOT={prefix}']
    if targets:
        cmd.append(f'BYPY_TARGETS={targets}')
    cmd += list(args)
    try:
        run_main(vm, *cmd)
    finally:
        from_vm(rsync, sources_dir, pkg_dir, output_dir, prefix=prefix)


if __name__ == '__main__':
    main()
