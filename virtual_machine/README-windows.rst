Download the Windows 10 ISO from:
https://www.microsoft.com/en-us/software-download/windows10ISO
and save as windows-install.iso

Download the VirtIO drivers ISO from:
https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/latest-virtio/
and save as virtio-win.iso

Create the SystemDisk with::

    qemu-img create -f qcow2 SystemDisk.qcow2 240G

Use the following ``install.sh``::

    qemu-system-x86_64 \
    --enable-kvm \
    -cpu host,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time \
    -smp cores=2,threads=4 \
    -m 8G \
    -drive file=SystemDisk.qcow2,index=0,media=disk,if=virtio \
    -drive file=windows-install.iso,index=1,media=cdrom \
    -drive file=virtio-win.iso,index=2,media=cdrom \
    -nic user,model=virtio-net-pci \
    -rtc base=localtime,clock=host \
    -usb -device usb-tablet

Skip entering the product key as windows 10 works fine without activation.

Choose Win10 Pro as the windows edition.

During installation, install the ``w10\viostor.inf`` driver so Windows can see
the virtio SystemDisk.

Make sure to set a password for the user account (user account named kovid)
as it will be needed for ssh login.

After installation to get networking, open Device manager locate the
network adapter with an exclamation mark icon (should be open), click Update
driver and select the virtual CD-ROM. Do not forget to select the checkbox
which says to search for directories recursively.

Now you can reboot, removing the two cdrom lines from above.

To setup Windows for use in a VM
----------------------------------

1) Start->Windows security
2) Turn off windows firewall on all network types
3) Under Virus and threat protection turn off everything
4) Start->Control Panel->search for power options
   - change to high performance plan and customize it to disable sleep and harddisk turn off
5) Start->gpedit.msc->Computer Configuration\Administrative Templates\Windows Components\Windows Update double click "Configure automatic updates" and set it to disabled and click apply and then OK
5) Start->Settings->User accounts->Sign in options->Require sign in->Never
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

Now restart the VM with::

    qemu-system-x86_64 \
    --enable-kvm \
    -cpu host,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time \
    -smp cores=2,threads=4 \
    -m 8G \
    -k en-us \
    -monitor unix:monitor.socket,server,nowait \
    -drive file=SystemDisk.qcow2,index=0,media=disk,if=virtio \
    -nic user,model=virtio-net-pci,hostfwd=tcp:0.0.0.0:0-:22 \
    -rtc base=localtime,clock=host \
    -usb -device usb-tablet

It should now be possible to SSH into the VM using::

    ssh -p `echo info usernet | socat - unix-connect:monitor.socket | grep HOST_FORWARD | tr -s ' ' '\t' | cut -f 5` kovid@localhost

Copy over .vimrc, .zshrc, .ssh/authorized_keys
Copy over the kitty terminfo using the ssh kitten

Edit /etc/sshd_config and set the following as we only want
login via key::

    PasswordAuthentication no
    KbdInteractiveAuthentication no
    UsePAM no
