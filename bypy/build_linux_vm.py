#!/usr/bin/env python
# License: GPLv3 Copyright: 2021, Kovid Goyal <kovid at kovidgoyal.net>


import json
import os
import shlex
import shutil
import subprocess
import sys

import yaml  # type: ignore

from virtual_machine.run import cmdline_for_machine_spec

from .chroot import Chroot
from .utils import current_dir

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def call(*args):
    if len(args) == 1:
        args = shlex.split(args[0])
    print(shlex.join(args))
    subprocess.check_call(args)


def build_chroot(chroot: Chroot):
    data = chroot.data_to_build_chroot()
    cp = subprocess.run([sys.executable, base, '__chroot__', 'bypy.chroot', 'build_chroot'], input=json.dumps(data).encode())
    raise SystemExit(cp.returncode)


def build_vm(chroot: Chroot):
    if os.path.exists(chroot.vm_path):
        shutil.rmtree(chroot.vm_path)
    os.makedirs(chroot.vm_path)
    if chroot.is_chroot_based:
        return build_chroot(chroot)
    user_data = chroot.cloud_init_config()
    user_data = '#cloud-config\n\n' + yaml.dump(user_data)
    meta_data = json.dumps({'instance-id': chroot.vm_name})
    cloud_image = chroot.cloud_image
    is_arm = chroot.image_arch == 'arm64'

    machine_spec = [
        f'-name {chroot.vm_name}',
        '-machine ' + ('virt' if is_arm else 'type=q35,accel=kvm'),
        '-cpu ' + ('max,pauth-impdef=on' if is_arm else 'host'),
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
    firmware = []
    disks = []
    drive_count = -1

    def add_efi_firmware():
        os.mkdir('firmware')
        fw = os.path.join(base, f'virtual_machine/firmware/{chroot.image_name}-arm64-efi.fd')
        code = 'firmware/efi-code.img'
        evars = 'firmware/efi-vars.img'
        call(f'dd if=/dev/zero of={code} bs=1M count=64')
        call(f'dd if={fw} of={code} conv=notrunc')
        call(f'dd if=/dev/zero of={evars} bs=1M count=64')
        firmware.append('# Firmware')
        firmware.append(f'-drive if=pflash,format=raw,readonly=on,unit=0,file="{code}"')
        firmware.append(f'-drive if=pflash,format=raw,readonly=off,unit=1,file="{evars}"')

    def add_disk(filename, disk_id):
        nonlocal drive_count
        drive_count += 1
        if False:
            disks.append('# A hard disk connected via SCSI for performance')
            disks.append(f'-device virtio-scsi-pci,id=scsi{drive_count}')
            disks.append(f'-drive file="{filename}",if=none,format=qcow2,discard=unmap,aio=native,cache=none,id={disk_id}')
            disks.append(f'-device scsi-hd,drive={disk_id},bus=scsi{drive_count}.0,serial={disk_id}')
        else:
            disks.append('# A hard disk connected via virtio-blk for performance')
            disks.append(f'-device virtio-blk-pci,drive=drive{drive_count},id={disk_id},num-queues=4')
            disks.append(f'-drive file="{filename}",if=none,format=qcow2,id=drive{drive_count}')

    with current_dir(chroot.vm_path):
        with open('user-data', 'w') as f:
            f.write(user_data)
        with open('meta-data', 'w') as f:
            f.write(meta_data)
        call('genisoimage -output cloud.img -volid cidata -joliet -rock user-data meta-data')
        call('qemu-img convert -f raw -O qcow2 cloud.img cloud-init.qcow2')
        os.remove('cloud.img')
        call('fallocate -l 64G SystemDisk.img')
        # we cannot create this here because newer ext4 filesystems have
        # orphan_file feature which the gues may not have, in which case
        # fsck fails for this disk. Instead create via cloud-init
        # call('mkfs.ext4 -L datadisk -F SystemDisk.img')
        call('qemu-img convert -f raw -O qcow2 SystemDisk.img SystemDisk.qcow2')
        os.remove('SystemDisk.img')
        if is_arm:
            add_efi_firmware()
        shutil.copy2(cloud_image, '.')
        converted = os.path.basename(cloud_image)
        call(f'qemu-img resize "{converted}" +8G')
        add_disk(converted, 'os_disk')
        add_disk('SystemDisk.qcow2', 'datadisk')
        add_disk('cloud-init.qcow2', 'cloud_init')

        machine_spec += firmware
        machine_spec += disks
        with open('machine-spec', 'w') as f:
            f.write('\n'.join(machine_spec))

    cmd = cmdline_for_machine_spec(machine_spec, 'monitor.socket')
    try:
        subprocess.check_call(cmd, cwd=chroot.vm_path)
    except KeyboardInterrupt:
        raise SystemExit('Exiting on keyboard interrupt')
