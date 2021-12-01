We dont need an actual VM for this, we can make use of QEMU's ability to run
ARM binaries on an Intel host. This we can build the ARM packages in a chroot
like the normal Linux binaries.
Based on: https://nerdstuff.org/posts/2020/2020-003_simplest_way_to_create_an_arm_chroot/

The following package names are for Arch Linux,
there are likely similar packages available for other distros.

First on the host machine, install the following packages from AUR::

    glib2-static
    pcre-static
    qemu-user-static
    binfmt-qemu-static

Then restart the binfmt service::

    systemctl restart systemd-binfmt.service

Now you can run programs in the chroot with::

    python ../bypy linux arm64 shell
