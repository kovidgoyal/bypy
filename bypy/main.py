#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import argparse
import atexit
import json
import os
import runpy
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

from .constants import (
    OS_NAME, OUTPUT_DIR, PREFIX, ROOT, SRC, SW, WORKER_DIR, build_dir, islinux,
    iswindows
)
from .deps import init_env, main as deps_main
from .utils import (
    RunShell, atomic_write, mkdtemp, rmtree, run_shell, single_instance
)


def option_parser():
    parser = argparse.ArgumentParser(description='Build dependencies')
    a = parser.add_argument
    a('deps', nargs='*', default=[], help='Which dependencies to build')
    a('--shell',
      default=False,
      action='store_true',
      help='Start a shell in the container')
    a('--clean',
      default=False,
      action='store_true',
      help='Remove previously built packages')
    a('--dont-strip',
      default=False,
      action='store_true',
      help='Dont strip the binaries when building')
    a('--compression-level',
      default='9',
      choices=list('123456789'),
      help='Level of compression for the Linux tarball')
    a('--skip-tests',
      default=False,
      action='store_true',
      help='Skip the tests when building')
    a('--sign-installers',
      default=False,
      action='store_true',
      help='Sign the binary installer, needs signing keys in the VMs')
    a('--notarize',
      default=False,
      action='store_true',
      help='Send the app for notarization to the platform vendor')
    a('--no-tty',
      default=False,
      action='store_true',
      help='Assume stdout is not a tty regardless of isatty()')
    a('--build-only',
      help='Build only a single extension module when building'
      ' program, useful for development')
    return parser


def build_program(args):
    init_env()
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


def daemonize():
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as e:
        raise SystemExit(f'fork #1 failed: {e}')

    # decouple from parent environment
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError as e:
        raise SystemExit(f'fork #2 failed: {e}')


def worker_single_instance():
    return single_instance('bypy_worker')


def worker_main(args):
    report_dir = os.environ['BYPY_WORKER']
    status_file_path = os.path.join(report_dir, 'status')
    if not worker_single_instance():
        atomic_write(status_file_path, 'EEXIST')
        raise SystemExit(1)
    if hasattr(os, 'fork'):
        daemonize()
    data = {'pid': os.getpid()}
    if hasattr(os, 'getsid'):
        data['sid'] = os.getsid(0)
    if hasattr(os, 'getpgid'):
        data['pgid'] = os.getpgid(0)
    atomic_write(status_file_path, json.dumps(data))
    atomic_write(os.path.join(WORKER_DIR, 'current_dir'), f'{report_dir}')
    rpath = os.path.join(report_dir, 'result')
    try:
        deps_main(args)
    except RunShell as rs:
        atomic_write(rpath, 'RUNSHELL:' + rs.serialized)
        return
    except (Exception, SystemExit) as e:
        atomic_write(rpath, 'ERROR:' + str(e))
        raise
    else:
        atomic_write(rpath, 'OK:')


def tail(report_dir, tail_end, rewind):
    with open(os.path.join(report_dir, 'output'), encoding='utf-8', errors='replace') as f:
        f.seek(-2048 if rewind else 0, os.SEEK_END)
        sleep_time = 0.05
        while not tail_end.is_set():
            data = f.read(4096)
            if data:
                sleep_time = 0.05
                print(end=data)
            else:
                print(end='', flush=True)
                sleep_time = min(sleep_time * 2, 1)
                tail_end.wait(sleep_time)
        data = f.read()
        if data:
            print(end=data, flush=True)


def clear_worker_dir(report_dir):
    if os.path.exists(report_dir):
        rmtree(report_dir)
    os.remove(os.path.join(WORKER_DIR, 'current_dir'))


def handle_status(report_dir):
    with open(os.path.join(report_dir, 'status')) as f:
        status = f.read()
    rewind = False
    if status == 'EEXIST':
        rewind = True
        with open(os.path.join(WORKER_DIR, 'current_dir')) as f:
            report_dir = f.read().strip()
        with open(os.path.join(report_dir, 'status')) as f:
            status = f.read()
    worker = json.loads(status)
    rpath = os.path.join(report_dir, 'result')
    tail_end = threading.Event()
    tailer = threading.Thread(target=tail, args=(report_dir, tail_end, rewind))
    tailer.start()
    try:
        while not os.path.exists(rpath):
            time.sleep(0.1)
    except KeyboardInterrupt:
        if iswindows:
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(worker['pid'])])
        else:
            os.killpg(int(worker['pgid']), signal.SIGINT)
        tail_end.set()
        tailer.join()
        print('', flush=True)
        print('\n\x1b[32mInterrupted by user, killing all worker processes and aborting\x1b[m', file=sys.stderr, flush=True)
        clear_worker_dir(report_dir)
        return
    finally:
        tail_end.set()
        tailer.join()
    time.sleep(0.1)  # give the worker process time to die
    result = open(rpath).read()
    rtype, data = result.split(':', 1)
    clear_worker_dir(report_dir)
    if rtype != 'OK':
        if rtype == 'ERROR':
            raise SystemExit(data)
        run_shell(**json.loads(data))
        raise SystemExit(1)


def run_worker(args, orig_args):
    orig_args = list(orig_args)
    orig_args.insert(1, 'main')
    tdir = tempfile.mkdtemp(dir=WORKER_DIR)
    d = os.path.dirname
    env = dict(os.environ)
    env['BYPY_WORKER'] = tdir
    cmd = [sys.executable, d(d(os.path.abspath(__file__)))] + orig_args[1:]
    with open(os.path.join(tdir, 'output'), 'wb') as output:
        p = subprocess.Popen(cmd, env=env, stdout=output, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    start = time.monotonic()
    status = os.path.join(tdir, 'status')
    while time.monotonic() - start < 5:
        if os.path.exists(status):
            return handle_status(tdir)
        time.sleep(0.02)
    if p.poll() is None:
        p.kill()
    print(cmd, file=sys.stderr)
    with open(os.path.join(tdir, 'output')) as f:
        print(end=f.read(), flush=True, file=sys.stderr)
    raise SystemExit('Timed out waiting for worker to write status')


def delete_code_signing_certs():
    cs = os.path.expanduser('~/code-signing')
    if os.path.exists(cs):
        shutil.rmtree(cs, ignore_errors=True)


def main(orig_args):
    args = option_parser().parse_args(orig_args[2:])
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(WORKER_DIR, exist_ok=True)
    building_program = args.deps == ['program']
    if building_program:
        atexit.register(delete_code_signing_certs)
    else:
        delete_code_signing_certs()

    if building_program:
        build_program(args)
    elif args.shell or args.deps == ['shell']:
        init_env()
        os.chdir(ROOT)
        run_shell(cwd=PREFIX)
    elif args.deps and args.deps[0] == 'bypy-worker-status':
        for x in args.deps[1:]:
            os.makedirs(os.path.expanduser(x), exist_ok=True)
        has_other = not worker_single_instance()
        raise SystemExit(13 if has_other else 0)
    else:
        if 'BYPY_WORKER' in os.environ:
            worker_main(args)
        else:
            run_worker(args, orig_args)


if __name__ == '__main__':
    main(sys.argv)
