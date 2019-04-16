#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import atexit
import ctypes
import errno
import fcntl
import os
import shlex
import shutil
import socket
import subprocess
import sys
import time

from .constants import LIBDIR, iswindows, worker_env

if iswindows:
    import msvcrt
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    get_file_type = k32.GetFileType
    get_file_type.argtypes = [wintypes.HANDLE]
    get_file_type.restype = wintypes.DWORD
    get_file_info_by_handle = k32.GetFileInformationByHandleEx
    get_file_info_by_handle.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    get_file_info_by_handle.restype = wintypes.BOOL

    def rmtree(x, tries=10):
        for i in range(tries):
            try:
                return shutil.rmtree(x)
            except WindowsError as err:
                if i >= tries - 1:
                    raise
                if err.winerror == 32:
                    # sharing violation (file open in another process)
                    time.sleep(1)
                    continue
                raise
else:
    rmtree = shutil.rmtree


hardlink = os.link


def print_cmd(cmd):
    print('\033[92m', end='')
    print(*cmd, end='\033[0m\n')


def call(*cmd, echo=True):
    if len(cmd) == 1 and isinstance(cmd[0], str):
        cmd = shlex.split(cmd[0])
    if echo:
        print_cmd(cmd)
    ret = subprocess.Popen(cmd).wait()
    if ret != 0:
        print('The failing command was:')
        print_cmd(cmd)
        raise SystemExit(ret)


def single_instance(name):
    address = '\0' + name.replace(' ', '_')
    sock = socket.socket(family=socket.AF_UNIX)
    try:
        sock.bind(address)
    except socket.error as err:
        if getattr(err, 'errno', None) == errno.EADDRINUSE:
            return False
        raise
    fd = sock.fileno()
    old_flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    fcntl.fcntl(fd, fcntl.F_SETFD, old_flags | fcntl.FD_CLOEXEC)
    atexit.register(sock.close)
    return True


def current_env(library_path=False):
    env = os.environ.copy()
    env.update(worker_env)
    if library_path:
        if library_path is True:
            library_path = LIBDIR
        else:
            library_path = library_path + os.pathsep + LIBDIR
        env['LD_LIBRARY_PATH'] = library_path
    return env


def isatty():
    if isatty.no_tty:
        return False
    f = sys.stdout
    if f.isatty():
        return True
    if not iswindows:
        return False
    # Check for a cygwin ssh pipe
    buf = ctypes.create_string_buffer(1024)
    h = msvcrt.get_osfhandle(f.fileno())
    if get_file_type(h) != 3:
        return False
    ret = get_file_info_by_handle(h, 2, buf, ctypes.sizeof(buf))
    if not ret:
        raise ctypes.WinError()
    data = buf.raw
    name = data[4:].decode('utf-16').rstrip(u'\0')
    parts = name.split('-')
    return (
        parts[0] == r'\cygwin' and parts[2].startswith('pty') and
        parts[4] == 'master')


isatty.no_tty = False


def run_shell(library_path=False):
    if not isatty():
        raise SystemExit('STDOUT is not a tty, aborting...')
    sh = 'C:/cygwin64/bin/zsh' if iswindows else '/bin/zsh'
    env = current_env(library_path=library_path)
    if iswindows:
        from .constants import cygwin_paths
        paths = env['PATH'].split(os.pathsep)
        paths = cygwin_paths + paths
        env['PATH'] = os.pathsep.join(paths)
    return subprocess.Popen([sh, '-i'], env=env).wait()


def lcopy(src, dst, no_hardlinks=False):
    try:
        if os.path.islink(src):
            linkto = os.readlink(src)
            os.symlink(linkto, dst)
            return True
        else:
            if no_hardlinks:
                shutil.copy(src, dst)
            else:
                os.link(src, dst)
            return False
    except FileExistsError:
        os.unlink(dst)
        return lcopy(src, dst)


def ensure_clear_dir(path):
    if os.path.exists(path):
        rmtree(path)
    os.makedirs(path)
