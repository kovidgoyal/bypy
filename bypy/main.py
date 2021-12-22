#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import atexit
import os
import runpy
import shutil
import subprocess
import sys
from contextlib import suppress

from .constants import (
    BYPY, OS_NAME, OUTPUT_DIR, ROOT, SRC, SW, WORKER_DIR, build_dir, islinux
)
from .deps import init_env, main as deps_main
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
        import traceback
        traceback.print_exc()
        run_shell()
    finally:
        os.chdir(SRC)
        rmtree(ext_dir), rmtree(bdir)
    if islinux:
        subprocess.run('sudo fstrim --all -v'.split())


def screen_exe():
    return shutil.which('screen')


def run_worker(args):
    screen = screen_exe()
    # first try to re-attach to a running session
    cmd = [screen, '-q', '-S', SCREEN_NAME, '-r']
    p = subprocess.Popen(cmd)
    logpath = os.path.join(WORKER_DIR, 'screenlog.0')
    try:
        rc = p.wait(5)
    except Exception:
        rc = None
    if rc is not None:
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


def build_deps(args):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(WORKER_DIR, exist_ok=True)
    delete_code_signing_certs()
    if 'BYPY_WORKER' in os.environ:
        os.chdir(os.environ['BYPY_WORKER'])
        deps_main(args)
    else:
        run_worker(args)
