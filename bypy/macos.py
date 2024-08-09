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
                os.path.join(base_dir(), 'macos.conf'))
    return ans


def singleinstance():
    name = f'bypy-macos-singleinstance-{os.getcwd()}'
    return single_instance(name)


def setup_parser(p):
    setup_build_parser(p)
    p.set_defaults(func=main)


def main(args):
    vm = get_vm_spec('macos')
    if args.action == 'shutdown':
        shutdown(vm)
        return
    port = wait_for_ssh(vm)
    conf = get_conf()
    rsync = Rsync(vm, port, rsync_cmd=conf.get('rsync', '/usr/local/bin/rsync'))
    output_dir = os.path.join(base_dir(), 'b', 'macos', 'dist')
    pkg_dir = os.path.join(base_dir(), 'b', 'macos', 'pkg')
    sources_dir = os.path.join(base_dir(), 'b', 'sources-cache')
    os.makedirs(sources_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(pkg_dir, exist_ok=True)

    prefix, python = conf['root'], conf['python']
    universal = conf.get('universal') == 'true'
    deploy_target = conf.get('deploy_target', '')
    ba = 'macos'
    cmd = [python, os.path.join(prefix, 'bypy'), f'BYPY_ROOT={prefix}', f'BYPY_ARCH={ba}']
    if universal:
        cmd.append('BYPY_UNIVERSAL=true')
    if deploy_target:
        cmd.append(f'BYPY_DEPLOY_TARGET={deploy_target}')

    if args.action == 'shell':
        return rsync.run_shell(sources_dir, pkg_dir, output_dir, cmd, ba, args, prefix=prefix)
    if args.action == 'reconnect':
        return rsync.reconnect(sources_dir, pkg_dir, output_dir, cmd, ba, args, prefix=prefix)

    if not singleinstance():
        raise SystemExit('Another instance of the macOS container is running')
    rsync.main(sources_dir, pkg_dir, output_dir, cmd, args, prefix=prefix)
