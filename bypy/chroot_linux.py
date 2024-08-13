#!/usr/bin/env python
# License: GPLv3 Copyright: 2024, Kovid Goyal <kovid at kovidgoyal.net>

import bz2
import codecs
import ctypes
import errno
import fcntl
import functools
import glob
import grp
import gzip
import importlib
import json
import lzma
import multiprocessing
import os
import pkgutil
import pwd
import re
import runpy
import shlex
import socket
import stat
import struct
import subprocess
import tarfile
import tempfile
import time
import traceback
import zipfile
import zlib
from contextlib import contextmanager, suppress
from enum import IntFlag, auto
from importlib import resources
from multiprocessing import dummy, pool, queues, synchronize
from operator import attrgetter
from typing import Literal, NamedTuple

# these cannot be imported after chroot so import them early
re, subprocess, bz2, lzma, zlib, tarfile, zipfile, glob, socket, struct, shlex, tempfile, time, functools, stat, fcntl, json, multiprocessing, pwd, grp, gzip, traceback, resources, codecs, pkgutil, runpy, dummy, pool, queues, synchronize

class MountOption(IntFlag):
    MS_RDONLY = auto()
    MS_NOSUID = auto()
    MS_NODEV = auto()
    MS_NOEXEC = auto()
    MS_SYNCHRONOUS = auto()
    MS_REMOUNT = auto()
    MS_MANDLOCK = auto()
    MS_DIRSYNC = auto()
    MS_NOSYMFOLLOW = auto()
    _ = auto()
    MS_NOATIME = auto()
    MS_NODIRATIME = auto()
    MS_BIND = auto()
    MS_MOVE = auto()
    MS_REC = auto()
    MS_SILENT = auto()
    MS_POSIXACL = auto()
    MS_UNBINDABLE = auto()
    MS_PRIVATE = auto()


class UnmountOption(IntFlag):
    MNT_FORCE = auto()
    MNT_DETACH = auto()
    MNT_EXPIRE = auto()
    UMOUNT_NOFOLLOW = auto()


def mount(source, target, fs='', flags: MountOption = MountOption(0), options: str = '', recursive_bind=False):
    if not fs:
        flags = MountOption.MS_BIND
        if recursive_bind:
            flags |= MountOption.MS_REC
    ret = ctypes.CDLL(None, use_errno=True).mount(source.encode(), target.encode(), fs.encode(), ctypes.c_ulong(int(flags)), options.encode() or None)
    if ret < 0:
        n = ctypes.get_errno()
        args = f'{os.strerror(n)}: {source=} {target=} {fs=} {flags=} {options=}'
        if n == errno.ENODEV:
            raise OSError(n, args, fs)
        raise OSError(n, args, source, None, target)


def umount(mountpoint: str, lazy: bool = False) -> None:
    flags = UnmountOption.UMOUNT_NOFOLLOW
    if lazy:
        flags |= UnmountOption.MNT_DETACH
    ret = ctypes.CDLL(None, use_errno=True).umount2(mountpoint.encode(), ctypes.c_int(int(flags)))
    if ret < 0:
        n = ctypes.get_errno()
        args = f'{os.strerror(n)}: {mountpoint=} {flags=}'
        raise OSError(n, args, mountpoint)


class IDRange(NamedTuple):
    first: int = 0
    num: int = 0


def find_largest_subid_map(which: Literal['uid', 'gid'], uid: int = -1) -> IDRange:
    candidates = [IDRange()]
    with suppress(FileNotFoundError), open(os.path.join('/etc', f'sub{which}')) as f:
        if uid < 0:
            uid = os.geteuid()
        uname = pwd.getpwuid(uid).pw_name
        quid = str(uid)

        for line in f:
            line = line.strip().replace(',', ':')
            if line:
                parts = line.split(':')
                if len(parts) > 2:
                    uname_or_uid, first, num = parts[:3]
                    if uname_or_uid in (uname, quid):
                        with suppress(Exception):
                            candidates.append(IDRange(int(first), int(num)))

    candidates.sort(key=attrgetter('num'))
    return candidates[-1]


def map_ids(child_pid: int, uid_range: IDRange, gid_range: IDRange) -> None:
    uid, gid = os.geteuid(), os.getegid()
    subprocess.check_call(f'newuidmap {child_pid} 0 {uid} 1 1 {uid_range.first} {uid_range.num}'.split())
    subprocess.check_call(f'newgidmap {child_pid} 0 {gid} 1 1 {gid_range.first} {gid_range.num}'.split())


def read_etc_environment():
    with open('/etc/environment') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            k, sep, v = line.partition('=')
            if not sep:
                continue
            if k.startswith('export '):
                k = k[len('export '):]
            if k:
                if len(v) > 1 and v[:1] in ('"', "'") and v[-1:] == v[:1]:
                    v = v[1:-1]
                if v:
                    os.environ[k] = v


class IPCEvent:

    def __enter__(self) -> 'IPCEvent':
        self.fd = os.eventfd(0)
        return self

    def __exit__(self, *a) -> None:
        os.close(self.fd)

    def set(self) -> None:
        os.eventfd_write(self.fd, 1)

    def wait(self) -> None:
        os.eventfd_read(self.fd)


class Fork:

    def __enter__(self) -> 'Fork':
        self.pid = os.getpid()
        self.child_pid = os.fork()
        self.in_child = self.child_pid == 0
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self.in_child:
            _, st = os.waitpid(self.child_pid, 0)
            if exc_val is None:
                raise SystemExit(os.waitstatus_to_exitcode(st))

    def map_ids(self, uid_range: IDRange, gid_range: IDRange) -> None:
        if self.child_pid:
            map_ids(self.child_pid, uid_range, gid_range)


class Resources:

    def __init__(self, chroot_path: str):
        self.chroot_path = chroot_path
        self.bind_mounts: dict[str, str] = {}
        self.fs_mounts: dict[str, str] = {}
        self.files: dict[str, str] = {}
        self.chroot_done = False
        self.do_cleanup = False

    def bind_mount(self, src: str, mountpoint: str) -> None:
        mp = os.path.join(self.chroot_path, mountpoint.lstrip(os.sep)).rstrip(os.sep)
        mount(src, mp, recursive_bind=True)
        self.bind_mounts[mountpoint or '/'] = mp

    def fs_mount(self, mountpoint: str, fstype: str, flags: MountOption, options: str = '') -> None:
        mp = os.path.join(self.chroot_path, mountpoint.lstrip(os.sep))
        mount(fstype, mp, fstype, flags, options)
        self.fs_mounts[mountpoint] = mp

    def symlink(self, target: str, location: str, cleanup: bool = True) -> None:
        lc = os.path.join(self.chroot_path, location.lstrip(os.sep))
        with suppress(FileNotFoundError):
            os.unlink(lc)
        os.symlink(target, lc)
        if cleanup:
            self.files[location] = lc

    def touch(self, path: str) -> None:
        with suppress(FileNotFoundError):
            os.unlink(path)
        open(path, 'w').close()

    def bind_file(self, path: str) -> None:
        dest = os.path.join(self.chroot_path, path.lstrip(os.sep))
        self.touch(dest)
        self.files[path] = dest
        mount(path, dest, recursive_bind=True)
        self.bind_mounts[path] = dest

    def bind_dev(self, name: str) -> None:
        src = os.path.join('/dev', name)
        self.bind_file(src)

    def chroot(self) -> None:
        os.chroot(self.chroot_path)
        self.chroot_done = True
        os.chdir('/')

    def __enter__(self) -> 'Resources':
        return self

    def __exit__(self, *a) -> None:
        if not self.do_cleanup:
            return
        def items(x: dict[str, str]):
            return reversed(tuple(x.keys() if self.chroot_done else x.values()))
        def lazy_umount(x: str) -> None:
            umount(x, lazy=True)
        tuple(map(umount, items(self.fs_mounts)))
        tuple(map(lazy_umount, items(self.bind_mounts)))
        tuple(map(os.unlink, items(self.files)))
        if self.chroot_done:
            subprocess.run(['chown', '-R', 'root:root', '/'])


def sanitize_env_vars(allowed=('TERM', 'COLORTERM', 'KITTY_WINDOW_ID', 'KITTY_PID',)) -> None:
    for key in tuple(os.environ):
        if key not in allowed:
            del os.environ[key]


def import_all_bypy_modules():
    def import_in(pkg):
        for res in resources.files(pkg).iterdir():
            b, ext = os.path.splitext(res.name)
            if ext == '.py' and b not in ('oem', 'mbcs'):
                importlib.import_module('.' + b, pkg)
    import_in('encodings')
    for res in resources.files('bypy').iterdir():
        if res.is_dir() and res.name != 'freeze':
            import_in('bypy.' + res.name)
    from bypy.freeze import prepare_for_chroot
    prepare_for_chroot()


@contextmanager
def chroot(path: str, bind_mounts: dict[str, str] | None = None):
    uid_map, gid_map = find_largest_subid_map('uid'), find_largest_subid_map('gid')
    if min(uid_map.num, gid_map.num) < 1024:
        raise SystemExit('Your user account does not have a sufficiently large sub UID and/or sub GID range defined,'
                         ' needed to run rootless containers. Use something like:'
                         ' sudo usermod --add-subuids 100000-165535 `whoami` --add-subgids 100000-165535')
    with IPCEvent() as unshared, IPCEvent() as mapped_to_root, Fork() as f, Resources(path) as r:
        if f.in_child:
            r.do_cleanup = True
            os.unshare(os.CLONE_NEWUSER | os.CLONE_NEWNS)
            unshared.set()
            mapped_to_root.wait()
            if os.geteuid():
                raise SystemExit(f'Parent process failed to map child process uid to root: {os.geteuid()=}')
            if os.getegid():
                raise SystemExit(f'Parent process failed to map child process gid to root: {os.getegid()=}')

            r.bind_mount(path, '')
            r.bind_file('/etc/resolv.conf')
            r.bind_mount('/sys', '/sys')
            for dev, proc in {'fd': 'fd', 'stdin': '0', 'stdout': '1', 'stderr': '2'}.items():
                r.symlink(f'/proc/self/fd/{proc}', f'/dev/{dev}')
            r.symlink('/dev/pts/ptmx', '/dev/ptmx')
            tuple(map(r.bind_dev, (
                'full', 'zero', 'tty', 'random', 'urandom', 'null',
            )))
            r.fs_mount('/run', 'tmpfs', MountOption.MS_NOSUID | MountOption.MS_NODEV, 'mode=0755')
            r.fs_mount('/tmp', 'tmpfs', MountOption.MS_NOSUID | MountOption.MS_NODEV, 'mode=1777')
            r.fs_mount('/dev/shm', 'tmpfs', MountOption.MS_NOSUID | MountOption.MS_NODEV, '')
            r.symlink('/dev/shm', '/run/shm', cleanup=False)  # auto-removed when /run is unmounted
            r.fs_mount('/dev/pts', 'devpts', MountOption.MS_NOSUID | MountOption.MS_NOEXEC, '')
            r.bind_mount('/proc', '/proc')
            for src, dest in (bind_mounts or {}).items():
                os.makedirs(os.path.join(path, dest.lstrip('/')), exist_ok=True)
                r.bind_mount(src, dest)
            from bypy.constants import in_chroot
            setattr(in_chroot, 'ans', True)
            import_all_bypy_modules()
            r.chroot()

            sanitize_env_vars()
            read_etc_environment()
            tempfile.tempdir = None
            tempfile.gettempdir()

            yield
        else:
            try:
                unshared.wait()
                f.map_ids(uid_map, gid_map)
            finally:
                mapped_to_root.set()


def develop(path: str = '/t/ubn'):
    print('Testing chroot to:', path)
    with chroot(path):
        print('In chroot')
        subprocess.check_call(['id'])
        subprocess.check_call(['mount'])
        subprocess.check_call(['ls', '-l'])
        subprocess.check_call(['cat', '-v', '/proc/self/cmdline'])
        print('\n')
        print('PATH=' + os.environ['PATH'])
        subprocess.check_call(['apt-get', 'update'])
        raise SystemExit(13)


if __name__ == '__main__':
    develop()
