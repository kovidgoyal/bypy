bypy can auto-build Linux VMs. In the project folder, just run::

    python ../bypy linux --arch 64 vm
    python ../bypy linux --arch arm64 vm

To build the VMs based on the base image specified in the projects
:file:`bypy/linux.conf` file.

.. note::

    Note that on Linux rather than use VMs, bypy will use a rootless container
    instead. In particular for building ARM it means you have to have to setup the
    ability to execute ARM binaries via QEMU and *binfmt*, as described `here
    <https://wiki.archlinux.org/title/QEMU#Chrooting_into_arm/arm64_environment_from_x86_64>`__.
