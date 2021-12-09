Creating QEMU Virtual machines for building
==============================================

See the README-macos.rst and README-windows.rst files for initial instructions
for creating the macOS and Windows Virtual machines.

Once you have these working, you just need to put them in a form bypy will
recognize. To do so create the directories
(inside the root directory of the project you want to build)::

    bypy/b/windows/vm
    bypy/b/macos/vm

Put the qcow2 and other files needed for each VM in its respective
directory.
Then create a machine-spec file in each directory that
contains the qemu command line used to launch the VM. For instance,
for Windows, one would have::

    # Number of processors
    -smp cores=2,threads=4
    # RAM
    -m 8G

    -cpu host,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time
    -drive file=SystemDisk.qcow2,index=0,media=disk,if=virtio
    -nic user,model=virtio-net-pci,hostfwd=tcp:0.0.0.0:0-:22
    -rtc base=localtime,clock=host
    -usb -device usb-tablet


You can run the VM by running the following command in the project root
directory::

    python ../bypy windows shell
    python ../bypy macos shell

And shut it down with::

    python ../bypy windows shutdown
    python ../bypy macos shutdown
