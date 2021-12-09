#!/usr/bin/env python
# License: GPLv3 Copyright: 2021, Kovid Goyal <kovid at kovidgoyal.net>


import json
import os
import shlex
import shutil
import subprocess

import yaml

from virtual_machine.run import cmdline_for_machine_spec

from .chroot import Chroot
from .utils import current_dir


def call(*args):
    if len(args) == 1:
        args = shlex.split(args[0])
    print(shlex.join(args))
    subprocess.check_call(args)


def build_vm(chroot: Chroot):
    if os.path.exists(chroot.vm_path):
        shutil.rmtree(chroot.vm_path)
    os.makedirs(chroot.vm_path)
    user_data = chroot.cloud_init_config()
    user_data = '#cloud-config\n\n' + yaml.dump(user_data)
    meta_data = json.dumps({'instance-id': chroot.vm_name})
    cloud_image = chroot.cloud_image
    is_arm = chroot.image_arch == 'arm64'

    machine_spec = [
        f'-name {chroot.vm_name}',
        '-machine ' + ('virt' if is_arm else 'type=q35,accel=kvm'),
        '-cpu ' + ('max' if is_arm else 'host'),
        '# num of cores',
        '-smp 4,cores=2',
        '# Amount of RAM',
        '-m 8G',
        '# Have a RNG in the VM based on the host RNG for performance',
        '-object rng-random,id=rng0,filename=/dev/urandom -device virtio-rng-pci,rng=rng0',
        '# Forward port 22 from the guest to a random port on the host',
        '# The romfile option prevents loading of PXE boot at startup',
        '-netdev user,id=n1,hostfwd=tcp:0.0.0.0:0-:22 -device virtio-net-pci,netdev=n1,romfile='
    ]
    disks = []
    scsi_count = -1

    def add_disk(filename, disk_id):
        nonlocal scsi_count
        scsi_count += 1
        disks.append('# A hard disk connected via SCSI for performance')
        disks.append(f'-device virtio-scsi-pci,id=scsi{scsi_count}')
        disks.append(f'-drive file="{filename}",if=none,format=qcow2,discard=unmap,aio=native,cache=none,id={disk_id}')
        disks.append(f'-device scsi-hd,drive={disk_id},bus=scsi{scsi_count}.0,serial={disk_id}')

    with current_dir(chroot.vm_path):
        with open('user-data', 'w') as f:
            f.write(user_data)
        with open('meta-data', 'w') as f:
            f.write(meta_data)
        call('genisoimage -output cloud.img -volid cidata -joliet -rock user-data meta-data')
        call('qemu-img convert -f raw -O qcow2 cloud.img cloud-init.qcow2')
        os.remove('cloud.img')
        call('fallocate -l 64G SystemDisk.img')
        call('mkfs.ext4 -L datadisk -F SystemDisk.img')
        call('qemu-img convert -f raw -O qcow2 SystemDisk.img SystemDisk.qcow2')
        os.remove('SystemDisk.img')
        os.mkdir('firmware')
        shutil.copy2(cloud_image, '.')
        add_disk(os.path.basename(cloud_image), 'os_disk')
        add_disk('SystemDisk.qcow2', 'datadisk')
        add_disk('cloud-init.qcow2', 'cloud_init')

        machine_spec += disks
        with open('machine-spec', 'w') as f:
            f.write('\n'.join(machine_spec))

    cmd = cmdline_for_machine_spec(machine_spec, 'monitor.socket')
    subprocess.check_call(cmd, cwd=chroot.vm_path)
