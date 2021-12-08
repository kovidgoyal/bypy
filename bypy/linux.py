#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import sys

from .chroot import Chroot, process_args


def main(args=tuple(sys.argv)):
    arch, args = process_args(args)
    chroot = Chroot(arch)
    if not chroot.single_instance():
        raise SystemExit('Another instance of the Linux container is running')
    try:
        if len(args) > 1:
            if args[1] == 'shutdown':
                return
            if args[1] == 'container':
                from .build_linux_vm import build_vm
                build_vm(chroot)
                return
        if not chroot.check_for_image():
            chroot.build_container()
        chroot.mount_image()
        chroot.run(args)
    finally:
        chroot.unmount_image()


if __name__ == '__main__':
    main()
