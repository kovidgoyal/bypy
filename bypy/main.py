#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import argparse
import atexit
import os
import runpy
import shutil
import subprocess
import sys
from contextlib import suppress

from .constants import BYPY, OS_NAME, OUTPUT_DIR, ROOT, SRC, SW, WORKER_DIR, build_dir, in_chroot, islinux
from .deps import init_env
from .deps import main as deps_main
from .utils import mkdtemp, rmtree, run_shell, setup_dependencies_parser

SCREEN_NAME = 'bypy-deps-worker'


def build_program(args):
    atexit.register(delete_code_signing_certs)
    init_env()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    init_env_module = runpy.run_path(os.path.join(
        SRC, 'bypy', 'init_env.py'),
        run_name='program')
    os.chdir(SRC)
    ext_dir, bdir = mkdtemp('plugins-'), mkdtemp('build-')
    build_dir(bdir)
    if 'build_c_extensions' in init_env_module:
        extensions_dir = init_env_module['build_c_extensions'](
                ext_dir, args)
        if args.build_only:
            dest = os.path.join(SW, 'dist', 'c-extensions')
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(extensions_dir, dest)
            print('C extensions built in', dest)
            return
    try:
        runpy.run_path(
            os.path.join(SRC, 'bypy', OS_NAME),
            init_globals={
                'args': args,
                'ext_dir': ext_dir,
                'init_env': init_env_module,
            },
            run_name='__main__')
    except Exception:
        if args.non_interactive:
            raise
        import traceback
        traceback.print_exc()
        run_shell()
    finally:
        os.chdir(SRC)
        rmtree(ext_dir), rmtree(bdir)
    if islinux and not in_chroot():
        subprocess.run('sudo fstrim --all -v'.split())


def screen_exe():
    return shutil.which('screen') or 'screen'


def setup_screen(clear_screen_dir=True, wipe_dead=True):
    screen = screen_exe()
    if islinux:
        screen_dir = os.path.join(WORKER_DIR, 'screen-sockets')
        if clear_screen_dir:
            with suppress(FileNotFoundError):
                shutil.rmtree(screen_dir)
        os.makedirs(screen_dir, exist_ok=True)
        os.chmod(screen_dir, 0o700)
        os.environ['SCREENDIR'] = screen_dir
    if wipe_dead:
        # wipe any dead sessions
        subprocess.Popen([screen, '-wipe']).wait()
    return screen


def run_worker(args):
    screen = setup_screen()
    logpath = os.path.join(WORKER_DIR, 'screenlog.0')
    # start a new session
    with open(os.path.expanduser('~/.screenrc'), 'w') as f:
        # allow scrolling with mousewheel/touchpad
        print('termcapinfo xterm* ti@:te@', file=f)
        # dont display startup message
        print('startup_message off', file=f)
        # use the alternate screen
        print('altscreen on', file=f)
    cmd = [screen, '-L', '-a', '-A', '-h', '6000', '-U', '-S', SCREEN_NAME]
    cmd += [sys.executable, BYPY] + sys.argv[1:]
    env = dict(os.environ)
    env['BYPY_WORKER'] = os.getcwd()
    with suppress(OSError):
        # remove any existing screen log from a previous run
        os.remove(logpath)
    # cwd so that screen log file is in worker dir
    p = subprocess.Popen(cmd, cwd=WORKER_DIR, env=env)
    rc = p.wait()
    # We do this via SH because running SH leaves the python stdout pipe in a funny
    # state where it substitutes U+2190 for ESC bytes. Running via cat avoids that
    subprocess.Popen(['cat', logpath]).wait()
    sys.stdout.flush()
    raise SystemExit(rc)


def delete_code_signing_certs():
    cs = os.path.expanduser('~/code-signing')
    if os.path.exists(cs):
        shutil.rmtree(cs, ignore_errors=True)


def check_worker_status(args):
    for x in args.directories:
        os.makedirs(os.path.expanduser(x), exist_ok=True)
    cp = subprocess.run([screen_exe(), '-q', '-ls', SCREEN_NAME])
    has_other = cp.returncode > 9
    raise SystemExit(13 if has_other else 0)


def setup_worker_status_parser(p):
    p.add_argument('directories', nargs='*', help='List of directories to create')
    p.set_defaults(func=check_worker_status)


def setup_build_deps_parser(p):
    setup_dependencies_parser(p)
    p.set_defaults(func=build_deps)


def setup_program_parser(p):
    from .utils import setup_program_parser as spp
    spp(p)
    p.set_defaults(func=build_program)


def shell(args):
    init_env()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    run_shell(library_path=True, cwd=ROOT)


def setup_shell_parser(p):
    p.set_defaults(func=shell)


def reconnect(args):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    screen = setup_screen(clear_screen_dir=False, wipe_dead=False)
    cmd = [screen, '-S', SCREEN_NAME, '-r']
    cp = subprocess.run(cmd)
    raise SystemExit(cp.returncode)


def setup_reconnect_parser(p):
    p.set_defaults(func=reconnect)


def sbom(args):
    import json
    import uuid
    from datetime import datetime

    from .download_sources import read_deps
    project = args.name
    project_id = f'SPDXRef-{project}'
    sbom_document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{project} SBOM",
        "documentNamespace": f"http://spdx.org/spdxdocs/{project}-sbom-{uuid.uuid4()}",
        "creationInfo": {
            "created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "creators": ["Tool: bypy", f'Person: {args.person}'],
        },
        "packages": [
            {
                "name": project,
                "SPDXID": project_id,
                "versionInfo": f"{args.version}",
                "downloadLocation": args.url or "NOASSERTION",
                "licenseConcluded": args.license,
            },
        ],
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relatedSpdxElement": project_id,
                "relationshipType": "DESCRIBES"
            }
        ],
    }
    for pkg in read_deps():
        package_spdx = pkg.sbom_spdx
        sbom_document["packages"].append(package_spdx)
        # Add a relationship to describe that the document describes this package
        sbom_document["relationships"].append({
            "spdxElementId": package_spdx["SPDXID"],
            "relatedSpdxElement": project_id,
            "relationshipType": 'BUILD_DEPENDENCY_OF' if pkg.for_building else 'DEPENDENCY_OF',
        })
    print(json.dumps(sbom_document, indent=2))


def setup_sbom_parser(p):
    p.add_argument('name', help='Project name')
    p.add_argument('version', help='Project version')
    p.add_argument('--license', default='GPL-3.0-only', help='Project license')
    p.add_argument('--url', default='', help='Project download URL')
    p.add_argument('--person', default='Kovid Goyal', help='Name of person creating this SBOM')
    p.set_defaults(func=sbom)


def build_deps(args):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(WORKER_DIR, exist_ok=True)
    delete_code_signing_certs()
    if in_chroot():
        deps_main(args)
    elif 'BYPY_WORKER' in os.environ:
        os.chdir(os.environ['BYPY_WORKER'])
        if islinux:
            # Try to get the kernel to prioritise the ssh daemon so we can log into the box after a disconnect
            # Needed on emulated VMs such as for ARM builds, in particular
            os.sched_setscheduler(0, os.SCHED_BATCH, os.sched_param(os.sched_get_priority_max(os.SCHED_BATCH)))
            os.nice(10)
        deps_main(args)
    else:
        run_worker(args)


def global_main(args):
    from bypy.export import setup_parser as export_setup_parser
    from bypy.linux import setup_parser as linux_setup_parser
    from bypy.macos import setup_parser as macos_setup_parser
    from bypy.windows import setup_parser as windows_setup_parser
    from virtual_machine.run import setup_parser as vm_setup_parser
    p = argparse.ArgumentParser(prog='bypy')
    s = p.add_subparsers(required=True)
    vm_setup_parser(s.add_parser('vm', help='Control the building and running of Virtual Machines'))
    linux_setup_parser(s.add_parser('linux', help='Build in a Linux VM'))
    macos_setup_parser(s.add_parser('macos', help='Build in a macOS VM'))
    windows_setup_parser(s.add_parser('windows', help='Build in a Windows VM', aliases=['win']))
    export_setup_parser(s.add_parser('export', help='Export built deps to a CI server'))
    setup_worker_status_parser(s.add_parser('worker-status', help='Check the status of the bypy dependency build worker'))
    setup_program_parser(s.add_parser('program', help='Build the program'))
    setup_build_deps_parser(s.add_parser('dependencies', aliases=['deps'], help='Build the dependencies'))
    setup_shell_parser(s.add_parser('shell', help='Run a shell with a completely initialized environment'))
    setup_sbom_parser(s.add_parser('sbom', help='Generate a SBOM which is printed to STDOUT in SPDX JSON format'))
    setup_reconnect_parser(s.add_parser('__reconnect__', help='For internal use'))
    parsed_args = p.parse_args(args[1:])
    parsed_args.func(parsed_args)
