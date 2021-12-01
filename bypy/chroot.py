#!/usr/bin/env python
# License: GPLv3 Copyright: 2021, Kovid Goyal <kovid at kovidgoyal.net>


import os
import pwd
import shlex
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from functools import partial
from urllib.request import urlopen

from .conf import parse_conf_file
from .constants import base_dir
from .utils import call, print_cmd, single_instance

RECOGNIZED_ARCHES = {
    'arm64': 'qemu-aarch64',
    '64': '', '32': ''
}


def cached_download(url):
    bn = os.path.basename(url)
    local = os.path.join('/tmp', bn)
    if not os.path.exists(local):
        print('Downloading', url, '...')
        data = urlopen(url).read()
        with open(local, 'wb') as f:
            f.write(data)
    return local


def get_mounts():
    ans = {}
    lines = open('/proc/self/mountinfo', 'rb').read().decode(
            'utf-8').splitlines()
    for line in lines:
        parts = line.split()
        src, dest = parts[3:5]
        ans[os.path.abspath(os.path.realpath(dest))] = src
    return ans


@contextmanager
def mounts_needed_for_install(img_path):
    mounts = []
    for dev in ('random', 'urandom'):
        mounts.append(os.path.join(img_path, f'dev/{dev}'))
        call('sudo', 'touch', mounts[-1])
        call('sudo', 'mount', '--bind', f'/dev/{dev}', mounts[-1])
    try:
        yield
    finally:
        for x in mounts:
            call('sudo', 'umount', '-l', x)


def install_modern_python(image_name):
    return [
        'add-apt-repository ppa:deadsnakes/ppa -y',
        'apt-get update',
        'apt-get install -y python3.9 python3.9-venv',
        ['sh', '-c', 'ln -sf `which python3.9` `which python3`'],
        'python3 -m ensurepip --upgrade --default-pip',
    ]


def install_modern_cmake(image_name):
    kitware = '/usr/share/keyrings/kitware-archive-keyring.gpg'
    return [
        ['sh', '-c',
         'curl https://apt.kitware.com/keys/kitware-archive-latest.asc |'
         f' gpg --dearmor - > {kitware}'],
        ['sh', '-c', f"echo 'deb [signed-by={kitware}]'"
            f' https://apt.kitware.com/ubuntu/ {image_name} main'
            ' > /etc/apt/sources.list.d/kitware.list'],
        'apt-get update',
        f'rm {kitware}',
        'apt-get install -y kitware-archive-keyring',
        'apt-get install -y cmake',
    ]


def process_args(args):
    args = list(args)
    arch = '64'
    if len(args) > 1 and args[1] in RECOGNIZED_ARCHES:
        arch = args[1]
        del args[1]
    return arch, args


class Chroot:

    def __init__(self, arch='64'):
        self.specified_arch = arch
        self.setarch_name = 'linux32' if arch == '32' else 'linux64'
        self.binfmt_misc_name = RECOGNIZED_ARCHES[arch]
        if self.binfmt_misc_name:
            if not os.path.exists(f'/proc/sys/fs/binfmt_misc/{self.binfmt_misc_name}'):
                raise SystemExit('Cannot execute ARM binaries on this computer. Read README-linux-arm.rst')
        self.image_arch = {'64': 'amd64', '32': 'i386', 'arm64': 'arm64'}[arch]
        self.sources_dir = os.path.join(base_dir(), 'b', 'sources-cache')
        os.makedirs(self.sources_dir, exist_ok=True)
        self.output_dir = os.path.join(base_dir(), 'b', 'linux', self.specified_arch)
        os.makedirs(self.output_dir, exist_ok=True)
        self.img_path = os.path.abspath(
            os.path.realpath(os.path.join(self.output_dir, 'chroot')))
        self.img_store_path = self.img_path + '.img'
        self.sw_dir = os.path.join(self.output_dir, 'sw')
        os.makedirs(self.sw_dir, exist_ok=True)
        self.conf = parse_conf_file(os.path.join(base_dir(), 'linux.conf'))
        self.image_mounted = False
        self.single_instance_name = f'bypy-{arch}-singleinstance-{os.getcwd()}'

    def single_instance(self):
        return single_instance(self.single_instance_name)

    def mount_image(self):
        if not self.image_mounted:
            call('sudo', 'mount', self.img_store_path, self.img_path)
            self.image_mounted = True

    def unmount_image(self):
        if self.image_mounted:
            call('sudo', 'umount', self.img_path)
            self.image_mounted = False

    @contextmanager
    def mounts_in_chroot(self, tdir):
        scall = partial(call, echo=False)
        current_mounts = get_mounts()
        base = os.path.dirname(os.path.abspath(__file__))

        def mount(src, dest, readonly=False):
            dest = os.path.join(self.img_path, dest.lstrip('/'))
            if dest not in current_mounts:
                scall('sudo', 'mkdir', '-p', dest)
                scall('sudo', 'mount', '--bind', src, dest)
                if readonly:
                    scall('sudo', 'mount', '-o', 'remount,ro,bind', dest)

        mount(tdir, '/tmp')
        mount(self.sw_dir, '/sw')
        mount(os.getcwd(), '/src', readonly=True)
        mount(self.sources_dir, '/sources')
        mount(os.path.dirname(base), '/bypy', readonly=True)
        mount('/dev', '/dev')
        scall('sudo', 'mount', '-t', 'proc', 'proc', os.path.join(self.img_path, 'proc'))
        scall('sudo', 'mount', '-t', 'sysfs', 'sys', os.path.join(self.img_path, 'sys'))
        scall('sudo', 'chmod', 'a+w', os.path.join(self.img_path, 'dev/shm'))
        scall('sudo', 'mount', '--bind', '/dev/shm', os.path.join(self.img_path, 'dev/shm'))
        try:
            yield
        finally:
            found = True
            while found:
                found = False
                for mp in sorted(get_mounts(), key=len, reverse=True):
                    if mp.startswith(self.img_path) and '/chroot/src/' not in mp:
                        call('sudo', 'umount', '-l', mp, echo=False)
                        found = True
                        break
            self.image_mounted = False

    def copy_terminfo(self):
        raw = subprocess.check_output(['infocmp']).decode('utf-8').splitlines()[0]
        path = raw.partition(':')[2].strip()
        if path and os.path.exists(path):
            bdir = os.path.basename(os.path.dirname(path))
            dest = os.path.join(self.img_path, 'usr/share/terminfo', bdir)
            call('sudo', 'mkdir', '-p', dest, echo=False)
            call('sudo', 'cp', '-a', path, dest, echo=False)

    def __call__(self, cmd, as_root=True, for_install=False):
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        print_cmd(['in-chroot'] + cmd)
        user = pwd.getpwuid(os.geteuid()).pw_name
        env = {
            'PATH': '/sbin:/usr/sbin:/usr/local/bin:/bin:/usr/bin',
            'HOME': '/root' if as_root else '/home/' + user,
            'XDG_RUNTIME_DIR': '/tmp/' + ('root' if as_root else user),
            'USER': 'root' if as_root else user,
            'TERM': os.environ.get('TERM', 'xterm-256color'),
            'BYPY_ARCH': self.image_arch,
        }
        if for_install:
            env['DEBIAN_FRONTEND'] = 'noninteractive'
        us = [] if as_root else ['--userspec={}:{}'.format(
            os.geteuid(), os.getegid())]
        as_arch = [self.setarch_name, '--']
        env_cmd = ['env']
        for k, v in env.items():
            env_cmd += [f'{k}={v}']
        cmd = ['sudo', 'chroot'] + us + [self.img_path] + as_arch + env_cmd + list(cmd)
        self.copy_terminfo()
        call('sudo', 'cp', '/etc/resolv.conf', os.path.join(self.img_path, 'etc'), echo=False)
        ret = subprocess.Popen(cmd, env=env).wait()
        if ret != 0:
            raise SystemExit(ret)

    def write_in_chroot(self, path, data):
        path = path.lstrip('/')
        p = subprocess.Popen([
            'sudo', 'tee', os.path.join(self.img_path, path)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        p.communicate(data)
        if p.wait() != 0:
            raise SystemExit(p.returncode)

    def run(self, args):
        zshrc = os.path.realpath(os.path.expanduser('~/.zshrc'))
        dest = os.path.join(
            self.img_path, 'home', pwd.getpwuid(os.geteuid()).pw_name, '.zshrc')
        if os.path.exists(zshrc):
            shutil.copy2(zshrc, dest)
        else:
            open(dest, 'wb').close()
        if 'KITTY_INSTALLATION_DIR' in os.environ:
            shi = os.path.join(os.environ['KITTY_INSTALLATION_DIR'], 'shell-integration', 'zsh', 'kitty.zsh')
            if os.path.exists(shi):
                shutil.copy2(shi, os.path.dirname(dest))

        # dont use /tmp since it could be RAM mounted and therefore too small
        with tempfile.TemporaryDirectory(prefix='tmp-', dir='bypy/b') as tdir, self.mounts_in_chroot(tdir):
            cmd = ['python3', '/bypy', 'main'] + args
            os.environ.pop('LANG', None)
            for k in tuple(os.environ):
                if k.startswith('LC') or k.startswith('XAUTH'):
                    del os.environ[k]
            self(cmd, as_root=False)

    def check_for_image(self):
        return os.path.exists(self.img_store_path)

    def _build_container(self, url):
        user = pwd.getpwuid(os.geteuid()).pw_name
        archive = cached_download(url.format(self.image_arch))
        image_name = url.split('/')[-1].split('-')[1]
        if os.path.exists(self.img_path):
            call('sudo', 'rm', '-rf', self.img_path, echo=False)
        if os.path.exists(self.img_store_path):
            os.remove(self.img_store_path)
        os.makedirs(self.img_path)
        call('truncate', '-s', '2G', self.img_store_path)
        call('mkfs.ext4', self.img_store_path)
        self.mount_image()
        call('sudo tar -C "{}" -xpf "{}"'.format(self.img_path, archive), echo=False)
        if os.getegid() != 100:
            self('groupadd -f -g {} {}'.format(os.getegid(), 'crusers'))
        self(
            'useradd --home-dir=/home/{user} --create-home'
            ' --uid={uid} --gid={gid} {user}'.format(
                user=user, uid=os.geteuid(), gid=os.getegid())
        )
        # Prevent services from starting
        self.write_in_chroot('/usr/sbin/policy-rc.d', '#!/bin/sh\nexit 101')
        self('chmod +x /usr/sbin/policy-rc.d')
        # prevent upstart scripts from running during install/update
        self('dpkg-divert --local --rename --add /sbin/initctl')
        self('cp -a /usr/sbin/policy-rc.d /sbin/initctl')
        self('''sed -i 's/^exit.*/exit 0/' /sbin/initctl''')
        # remove apt-cache translations for fast "apt-get update"
        self.write_in_chroot(
            '/etc/apt/apt.conf.d/chroot-no-languages',
            'Acquire::Languages "none";'
        )
        deps = self.conf['deps']
        if isinstance(deps, (list, tuple)):
            deps = ' '.join(deps)
        deps_cmd = 'apt-get install -y ' + deps

        extra_cmds = []
        needs_python = image_name in ('xenial', 'bionic')
        if needs_python:
            extra_cmds += install_modern_python(image_name)
        else:
            extra_cmds.append('apt-get install -y python-is-python3 python3-pip')
        needs_cmake = True
        if needs_cmake:
            extra_cmds += install_modern_cmake(image_name)
        else:
            extra_cmds.append('apt-get install -y cmake')

        tzdata_cmds = [
            f'''sh -c "echo '{x}' | debconf-set-selections"''' for x in (
                'tzdata tzdata/Areas select Asia',
                'tzdata tzdata/Zones/Asia select Kolkata'
            )] + ['debconf-show tzdata']

        with mounts_needed_for_install(self.img_path):
            for cmd in tzdata_cmds + [
                'apt-get update',
                # bloody only way to get tzdata to install non-interactively is to
                # pipe the expected responses to it
                """sh -c 'echo "6\\n44" | apt-get install -y tzdata'""",
                # Basic build environment
                'apt-get install -y build-essential software-properties-common'
                ' nasm chrpath zsh git uuid-dev libmount-dev apt-transport-https'
                ' dh-autoreconf gperf',
            ] + extra_cmds + [
                'python3 -m pip install ninja',
                'python3 -m pip install meson',
                deps_cmd,
                # Cleanup
                'apt-get clean',
                'chsh -s /bin/zsh ' + user,
            ]:
                if cmd:
                    if callable(cmd):
                        cmd()
                    else:
                        self(cmd, for_install=True)

    def build_container(self):
        url = self.conf['image']
        try:
            self._build_container(url=url)
        except Exception:
            failed_img_path = self.img_store_path + '.failed'
            if os.path.exists(failed_img_path):
                os.remove(failed_img_path)
            os.rename(self.img_store_path, failed_img_path)
            raise
