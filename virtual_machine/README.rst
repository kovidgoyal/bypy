Creating QEMU Virtual machines for building
==============================================

See the README-macos.rst and README-windows.rst files for initial instructions
for creating the macOS and Windows Virtual machines.

Once you have these working, you just need to put them in a form bypy will
recognize. To do so create the directories::

    /vms/macos-build
    /vms/windows-build

Put the qcow2 and other files needed for each VM in its respective
directory. It is important that the directory names contain ``macos`` and
``windows`` for macOS and Windows VMs, respectively.
Then create a machine-spec file in each directory that
contains the qemu command line used to launch the VM. For instance,
for windows, one would have::

    # Number of processors
    -smp cores=2,threads=4
    # RAM
    -m 8G

    -cpu host,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time
    -drive file=SystemDisk.qcow2,index=0,media=disk,if=virtio
    -nic user,model=virtio-net-pci,hostfwd=tcp:0.0.0.0:22003-:22
    -rtc base=localtime,clock=host
    -usb -device usb-tablet


Now you can run the VM using::

    python /path/to/bypy vm run windows-build
