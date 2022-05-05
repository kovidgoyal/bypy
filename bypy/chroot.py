#!/usr/bin/env python
# License: GPLv3 Copyright: 2021, Kovid Goyal <kovid at kovidgoyal.net>


import base64
import glob
import json
import os
import shlex
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


def install_modern_python(image_name):
    needs_python = image_name in ('xenial', 'bionic')
    if needs_python:
        yield 'start_custom_apt'
        yield 'add-apt-repository ppa:deadsnakes/ppa -y'
        yield 'apt-get update'
        yield 'apt-get install -y python3.9 python3.9-venv'
        yield ['sh', '-c', 'ln -sf `which python3.9` `which python3`']
        yield ['sh', '-c', 'ln -sf `which python3.9` /usr/local/bin/python']
        yield 'python3 -m ensurepip --upgrade --default-pip'
        yield 'end_custom_apt'
    else:
        yield 'apt-get install -y python-is-python3 python3-pip'


def install_modern_cmake(image_name):
    yield 'start_custom_apt'
    kitware = '/usr/share/keyrings/kitware-archive-keyring.gpg'
    yield ['sh', '-c', 'curl https://apt.kitware.com/keys/kitware-archive-latest.asc |' f' gpg --dearmor - > {kitware}']
    yield ['sh', '-c', f"echo 'deb [signed-by={kitware}]'" f' https://apt.kitware.com/ubuntu/ {image_name} main' ' > /etc/apt/sources.list.d/kitware.list']
    yield 'apt-get update'
    yield f'rm {kitware}'
    yield 'apt-get install -y kitware-archive-keyring'
    yield 'apt-get install -y cmake'
    yield 'end_custom_apt'


def p(x):
    return shlex.split(x) if isinstance(x, str) else list(x)


class Chroot:

    def __init__(self, arch='64'):
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
        self.vm_name_suffix = self.conf.get('vm_name_suffix', '')
        self.single_instance_name = f'bypy-{arch}-singleinstance-{os.getcwd()}'
        url = self.conf['image']
        self.image_name = url.split('/')[4]
        self.cloud_image_url = url.format(self.image_arch)
        self.vm_name = f'ubuntu-{self.image_name}-{self.image_arch}-{os.path.basename(os.getcwd())}{self.vm_name_suffix}'
        self.vm_path = os.path.abspath(
            os.path.realpath(os.path.join(self.output_dir, 'vm')))

    def single_instance(self):
        return single_instance(self.single_instance_name)

    def ensure_vm_is_built(self, spec):
        if spec.startswith('ssh:'):
            return
        if not os.path.exists(os.path.join(self.vm_path, 'SystemDisk.qcow2')):
            self.build_vm()

    def build_vm(self):
        from .build_linux_vm import build_vm
        build_vm(self)

    def container_deps_cmds(self):
        # Basic build environment
        yield p(
            'apt-get install -y build-essential software-properties-common'
            ' nasm chrpath zsh git uuid-dev libmount-dev apt-transport-https patchelf'
            ' dh-autoreconf gperf strace sudo vim screen zsh-syntax-highlighting'
        )
        for cmd in install_modern_python(self.image_name):
            yield p(cmd)
        for cmd in install_modern_cmake(self.image_name):
            yield p(cmd)
        yield p('python3 -m pip install ninja meson')

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

        def file(path, data, append=False, owner='root:root', permissions='0644', defer=False):
            if isinstance(data, str):
                data = data.encode('utf-8')
            content = base64.standard_b64encode(data).decode('ascii')
            files.append({
                'path': path, 'encoding': 'b64', 'owner': owner, 'append': append,
                'content': content, 'permissions': permissions, 'defer': defer})

        file('/etc/environment', f'\nBYPY_ARCH="{self.image_arch}"', append=True)
        file('/etc/systemd/journald.conf', 'SystemMaxUse=16M', append=True)
        user = USER
        for user_file in ('.zshrc', '.vimrc'):
            path = os.path.expanduser(f'~/{user_file}')
            if os.path.exists(path):
                file(f'/home/{user}/{user_file}', open(path).read(), owner=f'{user}:crusers', defer=True)

        if 'KITTY_INSTALLATION_DIR' in os.environ:
            shi = os.path.join(os.environ['KITTY_INSTALLATION_DIR'], 'shell-integration', 'zsh', 'kitty.zsh')
            if os.path.exists(shi):
                file(f'/home/{user}/kitty.zsh', open(shi).read(), owner=f'{user}:crusers', defer=True)
            ti = os.path.join(os.environ['KITTY_INSTALLATION_DIR'], 'terminfo', 'x', 'xterm-kitty')
            if os.path.exists(ti):
                file('/usr/share/terminfo/x/xterm-kitty', open(ti, 'rb').read())

        ans = {
            'growpart': {
                'mode': 'growpart',
                'devices': ['/'],
                'ignore_growroot_disabled': True,
            },
            'timezone': 'Asia/Kolkata',
            'fqdn': f'{self.vm_name}.localdomain',
            'package_upgrade': True,
            'groups': ['crusers'],
            'mounts': [["LABEL=datadisk", "/sw"]],
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
                    'groups': ['sudo'],
                    'sudo': ['ALL=(ALL) NOPASSWD:ALL'],
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

        a('apt-get clean')
        a('mkdir /sw/src /sw/sources /sw/bypy')
        a('ln -s /sw/src /src')
        a('ln -s /sw/sources /sources')
        a('ln -s /sw/bypy /bypy')
        a(f'chown -R {user}:crusers /sw')
        a('mv /tmp /sw')
        a('ln -s /sw/tmp /tmp')
        a('sh -c "rm -f /etc/resolv.conf; echo nameserver 8.8.4.4 > /etc/resolv.conf; echo nameserver 8.8.8.8 >> /etc/resolv.conf;'
          ' chattr +i /etc/resolv.conf; cat /etc/resolv.conf"')
        a('fstrim -v --all')
        a('poweroff')
        return ans

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
