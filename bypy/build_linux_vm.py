#!/usr/bin/env python
# License: GPLv3 Copyright: 2021, Kovid Goyal <kovid at kovidgoyal.net>


import json
import os
import shlex
import shutil
import subprocess

import yaml

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
    firmware_images = chroot.efi_firmware_images

    firmware = []
    disks = []
    scsi_count = -1

    def add_firmware(entry):
        e = firmware_images['mapping'][entry]
        d = 'firmware/' + os.path.basename(e['filename'])
        shutil.copy2(e['filename'], d)
        ro = 'on' if entry == 'executable' else 'off'
        firmware.append(f'-drive if=pflash,format={e["format"]},readonly={ro},file="{d}"')

    def add_disk(filename, disk_id):
        nonlocal scsi_count
        scsi_count += 1
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
        os.remove('qemu.img')
        call('fallocate -l 64G SystemDisk.img')
        call('mkfs.ext4 -L datadisk -F SystemDisk.img')
        call('qemu-img convert -f raw -O qcow2 SystemDisk.img SystemDisk.qcow2')
        os.remove('SystemDisk.img')
        os.mkdir('firmware')
        add_firmware('executable')
        add_firmware('nvram-template')
        shutil.copy2(cloud_image, '.')
        add_disk(os.path.basename(cloud_image), 'os_disk')
        add_disk('SystemDisk.qcow2', 'datadisk')
        add_disk('cloud-init.qcow2', 'cloud_init')
