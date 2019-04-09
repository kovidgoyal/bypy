#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>


import atexit
import errno
import fcntl
import shlex
import socket
import subprocess


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
