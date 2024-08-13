#!/usr/bin/env python
# License: GPLv3 Copyright: 2021, Kovid Goyal <kovid at kovidgoyal.net>


import base64
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
from contextlib import suppress
from urllib.request import urlopen

from .conf import parse_conf_file
from .constants import base_dir
from .utils import single_instance

try:
    import pwd
except ModuleNotFoundError:
    USER = os.environ.get('USER', 'kovid')
else:
    USER = pwd.getpwuid(os.geteuid()).pw_name


RECOGNIZED_ARCHES = {
    'arm64': 'qemu-aarch64',
    '64': '', '32': ''
}


def cached_download(url):
    bn = os.path.basename(url)
    d = os.path.join(os.path.expanduser('~/.cache/bypy/downloads'))
    os.makedirs(d, exist_ok=True)
    local = os.path.join(d, bn)
    if not os.path.exists(local):
        print('Downloading', url, '...')
        data = urlopen(url).read()
        with open(local, 'wb') as f:
            f.write(data)
    return local


def install_kitten(image_arch):
    arch = {'i386': '386'}.get(image_arch, image_arch)
    name = f'kitten-linux-{arch}'
    url = f'kitten-linux-{arch}'
    yield 'start_custom_apt'
    yield f'echo Downloading {url}'
    yield ['sh', '-c', f'curl -L https://github.com/kovidgoyal/kitty/releases/latest/download/{name} > /usr/local/bin/kitten']
    yield 'chmod a+x /usr/local/bin/kitten'
    yield 'kitten --version'
    yield 'end_custom_apt'



def install_modern_python(image_name, is_chroot_based):
    needs_python = image_name in ('xenial', 'bionic')
    if needs_python:
        build_deps = 'libssl-dev libbz2-dev libffi-dev liblzma-dev libncurses5-dev libreadline6-dev libsqlite3-dev zlib1g-dev lzma-dev'
        yield 'start_custom_apt'
        yield 'apt-get install -y ' + build_deps
        yield ['sh', '-c', 'curl -fsSL https://www.python.org/ftp/python/3.9.19/Python-3.9.19.tar.xz | tar xJ']
        yield ['sh', '-c', 'cd Python-* && ./configure -q && make -s -j4 && make install && rm -rf `pwd`']
        yield ['sh', '-c', 'ln -sf `which python3.9` `which python3`']
        yield ['sh', '-c', 'ln -sf `which python3.9` /usr/local/bin/python']
        yield 'python3 -m ensurepip --upgrade --default-pip'
        yield 'apt-get remove -y ' + build_deps
        yield 'end_custom_apt'
    else:
        yield 'apt-get install -y python-is-python3 python3-pip'


def latest_go_version(base: str) -> str:
    if base.count('.') > 1:
        return base
    from urllib.request import urlopen
    q = 'go' + base + '.'
    for r in json.loads(urlopen('https://go.dev/dl/?mode=json').read()):
        if r['version'].startswith(q):
            return r['version'][2:]
    return base + '.0'


def install_modern_go(image_name, image_arch, go_version='1.22.6'):
    go_version = latest_go_version(go_version)
    if image_arch == 'i386':
        image_arch = '386'
    gof = f'go{go_version}.linux-{image_arch}.tar.gz'
    yield 'start_custom_apt'
    yield f'echo Downloading {gof}'
    yield ['sh', '-c', f'curl -L https://go.dev/dl/{gof} > {gof}']
    yield 'rm -rf /usr/local/go'
    yield f'tar -C /usr/local -xzf {gof}'
    yield f'rm -f {gof}'
    yield 'ln -s /usr/local/go/bin/go /usr/local/bin/go'
    yield 'ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt'
    yield 'go version'
    yield 'end_custom_apt'


def install_modern_cmake(image_name):
    yield 'start_custom_apt'
    build_deps = 'libssl-dev'
    yield 'apt-get install -y ' + build_deps
    yield ['sh', '-c', 'curl -fsSL https://github.com/Kitware/CMake/releases/download/v3.30.2/cmake-3.30.2.tar.gz | tar xz']
    yield ['sh', '-c', 'cd cmake-* && ./bootstrap --parallel=4 --prefix=/usr && make -s -j4 && make install && rm -rf `pwd`']
    yield 'apt-get remove -y ' + build_deps
    yield 'end_custom_apt'


def p(x):
    return shlex.split(x) if isinstance(x, str) else list(x)


def files_to_copy(user=USER):

    home_path = '/root' if user == 'root' else f'/home/{user}'
    owner = 'root:root' if user == 'root' else f'{user}:crusers'

    def enc(x):
        if isinstance(x, str):
            x = x.encode()
        return base64.standard_b64encode(x).decode('ascii')


    def get_data(path):
        with open(path, 'rb') as f:
            return enc(f.read())

    ans = {}
    for user_file in ('.zshrc', '.vimrc'):
        path = os.path.expanduser(f'~/{user_file}')
        with suppress(FileNotFoundError):
            ans[f'{home_path}/{user_file}'] = {'owner': owner, 'defer': True, 'data': get_data(path)}
    return ans


def misc_commands():
    yield 'mkdir /sw/src /sw/sources /sw/bypy /sw/tmp /sw/pkg /sw/dist'
    yield 'ln -s /sw/src /src'
    yield 'ln -s /sw/sources /sources'
    yield 'ln -s /sw/bypy /bypy'


class Chroot:

    def __init__(self, arch, vmspec):
        self.vmspec = vmspec
        self.is_chroot_based = vmspec.startswith('chroot:')
        self.specified_arch = arch
        self.setarch_name = 'linux32' if arch == '32' else 'linux64'
        self.binfmt_misc_name = RECOGNIZED_ARCHES[arch]
        self.image_arch = {'64': 'amd64', '32': 'i386', 'arm64': 'arm64'}[arch]
        self.qemu_arch = {'64': 'x86_64', '32': 'i386', 'arm64': 'aarch64'}[arch]
        self.sources_dir = os.path.join(base_dir(), 'b', 'sources-cache')
        os.makedirs(self.sources_dir, exist_ok=True)
        self.output_dir = os.path.join(base_dir(), 'b', 'linux', self.specified_arch)
        os.makedirs(self.output_dir, exist_ok=True)
        self.img_path = os.path.abspath(
            os.path.realpath(os.path.join(self.output_dir, 'chroot')))
        self.img_store_path = self.img_path + '.img'
        self.conf = parse_conf_file(os.path.join(base_dir(), 'linux.conf'))
        self.go_version = ''
        gomod = os.path.join(os.path.dirname(base_dir()), 'go.mod')
        if os.path.exists(gomod):
            with open(gomod) as f:
                raw = f.read()
            m = re.search(r'^go\s+(\S+)', raw, flags=re.M)
            if m:
                self.go_version = m.group(1)
        self.vm_name_suffix = self.conf.get('vm_name_suffix', '')
        self.single_instance_name = f'bypy-{arch}-singleinstance-{os.getcwd()}'
        url = self.conf['image']
        if arch == 'arm64' and ('20.04' in url or '18.04' in url) and not self.is_chroot_based:
            # Older Ubuntu ARM images fail to boot with up-to-date QEMU/OVMF
            url = 'https://cloud-images.ubuntu.com/releases/jammy/release/ubuntu-22.04-server-cloudimg-{}.img'
        self.image_name = url.split('/')[4]
        self.cloud_image_url = url.format(self.image_arch)
        if self.is_chroot_based:
            self.cloud_image_url = self.cloud_image_url.rpartition('.')[0] + '-root.tar.xz'
        self.vm_name = f'ubuntu-{self.image_name}-{self.image_arch}-{os.path.basename(os.getcwd())}{self.vm_name_suffix}'
        self.vm_path = os.path.abspath(
            os.path.realpath(os.path.join(self.output_dir, 'chroot' if self.is_chroot_based else 'vm')))

    def single_instance(self):
        return single_instance(self.single_instance_name)

    def build_vm(self):
        if self.is_chroot_based:
            self.build_chroot()
        else:
            from .build_linux_vm import build_vm
            build_vm(self)

    def container_deps_cmds(self):
        # Basic build environment
        yield p(
            'apt-get install -y build-essential software-properties-common'
            ' nasm chrpath zsh git uuid-dev libmount-dev apt-transport-https patchelf'
            ' dh-autoreconf gperf strace sudo vim screen zsh-syntax-highlighting'
        )
        for cmd in install_kitten(self.image_arch):
            yield p(cmd)
        if self.go_version:
            for cmd in install_modern_go(self.image_name, self.image_arch, self.go_version):
                yield p(cmd)
        for cmd in install_modern_cmake(self.image_name):
            yield p(cmd)
        for cmd in install_modern_python(self.image_name, self.is_chroot_based):
            yield p(cmd)
        yield p('python3 -m pip install --upgrade pip')
        # html5lib needed for qt-webengine
        yield p('python3 -m pip install ninja packaging meson certifi html5lib')

        deps = self.conf['deps']
        if isinstance(deps, (list, tuple)):
            deps = ' '.join(deps)
        deps_cmd = 'apt-get install -y ' + deps
        yield p(deps_cmd)
        yield p('apt-get clean')

    def cloud_init_config(self):
        packages = []
        ans = {}
        cmds = []
        sources = {}
        files = []
        try:
            ssh_authorized_keys = [x.strip() for x in open(os.path.expanduser('~/.ssh/authorized_keys'))]
        except FileNotFoundError:
            ssh_authorized_keys = []

        def file(path, data, append=False, owner='root:root', permissions='0644', defer=False, needs_encoding=True):
            if needs_encoding:
                if isinstance(data, str):
                    data = data.encode('utf-8')
                content = base64.standard_b64encode(data).decode('ascii')
            else:
                content = data
            files.append({
                'path': path, 'encoding': 'b64', 'owner': owner, 'append': append,
                'content': content, 'permissions': permissions, 'defer': defer})

        file('/etc/environment', f'\nBYPY_ARCH="{self.image_arch}"', append=True)
        file('/etc/systemd/journald.conf', '\nSystemMaxUse=16M', append=True)
        file('/etc/apt/apt.conf.d/99-auto-upgrades', 'APT::Periodic::Update-Package-Lists "0";\nAPT::Periodic::Unattended-Upgrade "0";')

        # On ARM especially the disks are occasionally not mounted or mounted readonly
        file('/usr/local/bin/fix-mounting', '''\
#!/bin/sh
mount -a
mount -o remount,rw --target /
mount -o remount,rw --target /sw
date >> /root/fix-mounting-ran-at
''', permissions='0755')
        file('/etc/cron.d/fix-mounting', '@reboot root /usr/local/bin/fix-mounting')

        user = USER
        for path, spec in files_to_copy(user):
            file(path, spec['data'], owner=spec.get('owner', 'root:root'), defer=spec.get('defer', False))

        ans = {
            'fs_setup': [
                {
                    'label': 'datadisk',
                    'filesystem': 'ext4',
                    'device': '/dev/vdb',
                },
            ],
            'growpart': {
                'mode': 'growpart',
                'devices': ['/'],
                'ignore_growroot_disabled': True,
            },
            'timezone': 'Asia/Kolkata',
            'fqdn': f'{self.vm_name}.localdomain',
            'package_upgrade': True,
            'groups': ['crusers'],
            'mounts': [
                ["LABEL=datadisk", "/sw"],
            ],
            'apt': {
                'preserve_sources_list': True,
                'sources': sources,
            },
            'write_files': files,
            'users': [
                {
                    'name': user,
                    'shell': '/bin/zsh',
                    'primary_group': 'crusers',
                    'groups': 'sudo',
                    'sudo': 'ALL=(ALL) NOPASSWD:ALL',
                    'no_user_group': True,
                    'ssh_authorized_keys': ssh_authorized_keys,
                }
            ],
            'packages': packages,
            'runcmd': cmds,
        }
        process_apt = True
        for cmd in self.container_deps_cmds():
            if not cmd:
                continue
            if cmd[0] == 'add-apt-repository':
                sources[f'ignored{len(sources)+1}'] = {'source': cmd[1]}
            elif cmd[0] == 'start_custom_apt':
                process_apt = False
            elif cmd[0] == 'end_custom_apt':
                process_apt = True
            elif cmd[0] == 'apt-get' and process_apt:
                for x in cmd[1:]:
                    if not x.startswith('-') and x not in ('update', 'install', 'clean'):
                        packages.append(x)
            else:
                cmds.append(cmd)

        def a(x):
            cmds.append(p(x))

        # Nuke snap
        a('systemctl disable snapd.service snapd.socket snapd.seeded.service')
        a('snap remove --purge lxd')
        a('snap remove --purge core20')
        a('snap remove --purge snapd')
        a('apt autoremove -y snapd')
        a('rm -rf /var/cache/snapd/')

        # removing cloud-init crashes
        # a('apt-get remove -y cloud-init')
        a('apt-get clean')
        tuple(map(a, misc_commands()))
        a(f'chown -R {user}:crusers /sw')
        a('sh -c "rm -f /etc/resolv.conf; echo nameserver 8.8.4.4 > /etc/resolv.conf; echo nameserver 8.8.8.8 >> /etc/resolv.conf;'
          ' chattr +i /etc/resolv.conf; cat /etc/resolv.conf"')
        a('fstrim -v --all')
        a('poweroff')
        return ans

    def build_chroot(self):
        import stat
        import tarfile

        def tar_filter(member: tarfile.TarInfo, path):
            if member.isreg() or member.isdir() or member.islnk() or member.issym():
                if member.name == 'etc/resolv.conf':
                    return
                member.mode |= stat.S_IWRITE | stat.S_IREAD
                return member

        print('Extracting base image...')
        with suppress(FileNotFoundError):
            shutil.rmtree(self.vm_path)
        os.makedirs(self.vm_path)
        with tarfile.open(self.cloud_image) as tf:
            tf.extractall(self.vm_path, filter=tar_filter)
        shell = '/bin/zsh'

        extra_env = {
            'BYPY_ARCH': self.image_arch,
            'SHELL': shell,
            'EDITOR': '/usr/bin/vim',
            'HOME': '/root',
            'LANG': 'en_US.UTF-8',
            'TMPDIR': '/sw/tmp',
            'TEMP': '/sw/tmp',
            'TMP': '/sw/tmp',
            'QT_QPROCESS_NO_VFORK': '1',
        }
        files = files_to_copy('root')
        deps_cmds = tuple(cmd for cmd in self.container_deps_cmds() if cmd not in (['start_custom_apt'], ['end_custom_apt']))
        def c(*a: str) -> tuple[list[str], ...]:
            return tuple(map(p, a))
        commands = c(
            'apt-get update -y',
            'apt-get upgrade -y'
            ) + deps_cmds + c(
            'apt-get remove -y cloud-init',
            'apt-get upgrade -y',
            'apt-get clean -y',
            'mkdir /sw',
            f'chsh -s {shell} root',
        ) + c(*misc_commands())
        from .chroot_linux import chroot

        with chroot(self.vm_path):
            with open('/etc/environment', 'a') as f:
                print(file=f)
                for key, val in extra_env.items():
                    print(f'{key}={shlex.quote(val)}', file=f)
                    if key not in ('TMPDIR', 'TMP', 'TEMP'):
                        os.environ[key] = val

            for path, m in files.items():
                with open(path, 'wb') as f:
                    f.write(base64.standard_b64decode(m['data']))

            for cmd in commands:
                print('\x1b[32m' + shlex.join(cmd) + '\x1b[0m')  # ]]
                cp = subprocess.run(cmd)
                if cp.returncode:
                    raise SystemExit(cp.returncode)
            SSL_CERT_FILE = subprocess.check_output(['python3', '-m', 'certifi']).decode().strip()
            with open('/etc/environment', 'a') as f:
                print(f'SSL_CERT_FILE={shlex.quote(SSL_CERT_FILE)}', file=f)
            print('Chroot created successfully at:', self.vm_path)

    def run_func(self, sources_dir: str, pkg_dir: str, output_dir: str, func, *args, **kwargs):
        from .chroot_linux import chroot
        bypy_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with chroot(self.vm_path, {bypy_src: '/sw/bypy', sources_dir: '/sw/sources', pkg_dir: '/sw/pkg', output_dir: '/sw/dist'}):
            os.chdir(os.path.expanduser('~'))
            func(*args, **kwargs)

    @property
    def cloud_image(self):
        return cached_download(self.cloud_image_url)

    @property
    def efi_firmware_images(self):
        for x in glob.glob('/usr/share/qemu/firmware/*.json'):
            with open(x) as f:
                raw = f.read()
            data = json.loads(raw)
            if 'uefi' in data.get('interface-types', ()) and 'secure-boot' not in data.get('features', ()):
                for target in data['targets']:
                    if target['architecture'] == self.qemu_arch:
                        return data
