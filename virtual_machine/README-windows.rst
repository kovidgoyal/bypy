Download the Windows 10 ISO from:
https://www.microsoft.com/en-us/software-download/windows11
If Microsoft blocks you from downloading the ISO, instead download the media
creation tool from the same website and create the ISO. This can be done on
windows computer or using WINE (I assume).

Save the ISO as ``windows-install.iso``

Download the VirtIO drivers ISO from:
https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/latest-virtio/
and save as virtio-win.iso

Use the following ``install.py``:

.. code-block:: py

    #!/usr/bin/python
    # Copyright (C) 2025 Kovid Goyal <kovid at kovidgoyal.net>

    import contextlib
    import os
    import subprocess

    # Windows 11 needs both secure boot and TPM so that complicates life
    # The OVMF firmware files can be obtained by following the instructions at:
    # https://wiki.archlinux.org/title/QEMU (search for secure boot)
    tpm_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tpm')
    tpm_path = os.path.join(tpm_dir, 'swtpm.sock')
    os.makedirs(tpm_dir, exist_ok=True)
    if not os.path.exists('SystemDisk.qcow2'):
        subprocess.check_call('qemu-img create -f qcow2 SystemDisk.qcow2 240G'.split())

    p = subprocess.Popen(f'swtpm socket --tpmstate dir={tpm_dir} --ctrl type=unixio,path={tpm_path},terminate --tpm2'.split())
    try:
        subprocess.run(('qemu-system-x86_64'
        ' --enable-kvm '
        ' -cpu host,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time,+aes,+vmx'
        ' -m 8G'
        ' -smp 4,sockets=1,cores=4,threads=1'
        ' -machine type=q35,accel=kvm'
        # TPM
        f' -chardev socket,id=chrtpm,path={tpm_path}'
        ' -tpmdev emulator,id=tpm0,chardev=chrtpm'
        ' -device tpm-tis,tpmdev=tpm0'
        # Disks
        ' -drive file=SystemDisk.qcow2,index=0,media=disk,if=virtio'
        ' -drive file=windows-install.iso,index=1,media=cdrom'
        ' -drive file=virtio-win.iso,index=2,media=cdrom'
        ' -rtc base=localtime,clock=host'
        # USB input devices
        ' -usb -device usb-tablet -device usb-kbd'
        # Network card
        ' -nic user,model=virtio-net-pci'
        # EFI firmware with secureboot keys
        ' -drive if=pflash,format=raw,readonly=on,file=OVMF_CODE.secboot.4m.fd'
        ' -drive if=pflash,format=raw,file=OVMF_VARS_4M.secboot.fd '
        # Display
        ' -vga virtio').split())
    finally:
        if p.poll() is None:
            p.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                p.wait(0.1)
            if p.poll() is None:
                p.kill()
            p.wait()

Skip entering the product key as windows 10 and 11 work fine without activation.

Choose Windows Pro as the windows edition.

During installation, install the storage driver from ``viostor\w10\amd64`` so Windows can see
the virtio SystemDisk. Similarly install the virtio networking driver later
in the installation by choosing ``NetKVM`` as the folder on the cdrom to
install drivers from.

Skip the creation of a Microsoft account by pressing ``Shift+F10`` at the sign
in screen to get a command prompt and then running::

    start ms-cxh:localonly

Make sure to set a password for the user account (user account named kovid)
as it will be needed for ssh login.

Browse to ``E:\`` drive and install the Balloon virtio driver by right clicking on
``balloon.inf`` and selecting install. Similarly install the input and memory
and fs and gpu drivers.

Now you can reboot, removing the two cdrom lines from above.

To setup Windows for use in a VM
----------------------------------

1) Start->Windows security
2) Turn off windows firewall on all network types
3) Under Virus and threat protection turn off everything
4) Start->Control Panel->search for power options
   - change to high performance plan (under additional plans) and customize it to disable sleep, monitor and harddisk turn off
5) Start->gpedit.msc->Computer Configuration\Administrative Templates\Windows Components\Windows Update\Manage end user experience -> double click "Configure automatic updates" and set it to disabled and click apply and then OK
6) Start->Settings->System->About->Rename this PC
7) Run services.msc find the Windows search service and double click it, then disable it from starting this turns off content indexing improving performance

Setup automatic logon as described here:
https://support.microsoft.com/en-in/help/324737/how-to-turn-on-automatic-logon-in-windows

Install Cygwin
----------------

Install cygwin with the packages: vim, dos2unix, rsync, openssh, unzip, wget, make, zsh, patch, bash-completion, curl, screen

Edit /etc/nsswitch.conf and change db_shell to /bin/zsh

Start a cygwin administrator prompt (right click and run as administrator). In
it, run::

    editrights.exe -a SeAssignPrimaryTokenPrivilege -u kovid
    editrights.exe -a SeCreateTokenPrivilege -u kovid
    editrights.exe -a SeTcbPrivilege -u kovid
    editrights.exe -a SeServiceLogonRight -u kovid
    editrights.exe -a SeCreateSymbolicLinkPrivilege -u kovid
    ssh-host-config

Say no for StrictMode and yes or default for all other questions. Run::

    net start cygsshd

Now create the file ``machine-spec``::

    -cpu host,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time,+aes,+vmx
    -m 4G
    -smp 4,sockets=1,cores=4,threads=1
    -machine type=q35,accel=kvm
    # TPM
    -chardev socket,id=chrtpm,path=tpm/swtpm.sock
    -tpmdev emulator,id=tpm0,chardev=chrtpm
    -device tpm-tis,tpmdev=tpm0
    # Disks
    -drive file=SystemDisk.qcow2,index=0,media=disk,if=virtio
    -rtc base=localtime,clock=host
    # USB input devices
    -usb -device usb-tablet -device usb-kbd
    # Network
    -netdev user,id=net0,hostfwd=tcp:0.0.0.0:0-:22
    -device virtio-net-pci,netdev=net0
    # EFI firmware with secureboot keys
    -drive if=pflash,format=raw,readonly=on,file=OVMF_CODE.secboot.4m.fd
    -drive if=pflash,format=raw,file=OVMF_VARS_4M.secboot.fd


Run the new VM with::

    bypy vm run --with-gui `pwd`


Copy over .vimrc, .zshrc, .ssh/authorized_keys
Copy over the kitty terminfo using the ssh kitten

Edit /etc/sshd_config and set the following as we only want
login via key::

    PasswordAuthentication no
    KbdInteractiveAuthentication no
    UsePAM no
