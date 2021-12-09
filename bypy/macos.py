#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys

from virtual_machine.run import shutdown, wait_for_ssh

from .conf import parse_conf_file
from .constants import base_dir
from .utils import single_instance
from .vms import Rsync, get_vm_spec


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
    prefix, python = conf['root'], conf['python']
    vm = get_vm_spec('macos')
    universal = conf.get('universal') == 'true'
    deploy_target = conf.get('deploy_target', '')
    if len(args) > 1:
        if args[1] == 'shutdown':
            shutdown(vm)
            return
    port = wait_for_ssh(vm)
    rsync = Rsync(vm, port)
    output_dir = os.path.join(base_dir(), 'b', 'macos', 'dist')
    pkg_dir = os.path.join(base_dir(), 'b', 'macos', 'pkg')
    sources_dir = os.path.join(base_dir(), 'b', 'sources-cache')
    os.makedirs(sources_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(pkg_dir, exist_ok=True)

    cmd = [
        python, os.path.join(prefix, 'bypy'), 'main',
        f'BYPY_ROOT={prefix}']
    if universal:
        cmd.append('BYPY_UNIVERSAL=true')
    if deploy_target:
        cmd.append(f'BYPY_DEPLOY_TARGET={deploy_target}')
    cmd += list(args)
    rsync.main(sources_dir, pkg_dir, output_dir, cmd, prefix=prefix)


if __name__ == '__main__':
    main()
