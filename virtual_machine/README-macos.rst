On the Linux machine::

    git clone https://github.com/kholia/OSX-KVM.git && cd OSX-KVM && \
    ./fetch-macOS-v2.py -s sonoma && \
    dmg2img -i BaseSystem.dmg BaseSystem.img && \
    qemu-img create -f qcow2 mac_hdd_ng.img 240G && \
    echo 1 | sudo tee /sys/module/kvm/parameters/ignore_msrs


Edit OpenCore-Boot.sh, replacing Penryn with Haswell-noTSX and change the
``-device vmware-svga`` line to:

  -display gtk,zoom-to-fit=on

Run the machine with::

    ./OpenCore-Boot.sh

Use arrow keys and enter to boot the macOS base system image. Once booted,
install the OS:

* First, run Disk Utility and create a single APFS partition named ``SystemDisk`` to install to.
  Then quit disk utility and choose: Reinstall macos Sonoma.

* Create a user account named: ``kovid`` during OS installation

Run::

    mkdir macos && \
    mv mac_hdd_ng.img macos/SystemDisk.qcow2 && \
    cp OVMF*.fd macos/ && \
    cp OpenCore/OpenCore.qcow2 macos/ && \
    cd macos

Create the following :file:`machine-spec` file based on OpenCore-Boot.sh::

    # Processors
    -smp 4,cores=2,sockets=1
    # RAM
    -m 4G

    -enable-kvm
    -cpu Haswell-noTSX,kvm=on,vendor=GenuineIntel,+invtsc,vmware-cpuid-freq=on,+ssse3,+sse4.2,+popcnt,+avx,+aes,+xsave,+xsaveopt,check
    -machine q35
    -device qemu-xhci,id=xhci
    -device usb-kbd,bus=xhci.0
    -device usb-tablet,bus=xhci.0
    -device usb-ehci,id=ehci
    -device isa-applesmc,osk="ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"
    -drive if=pflash,format=raw,readonly=on,file="OVMF_CODE.fd"
    -drive if=pflash,format=raw,file="OVMF_VARS-1920x1080.fd"
    -smbios type=2
    -device ich9-intel-hda
    -device hda-duplex
    -device ich9-ahci,id=sata
    -drive id=OpenCoreBoot,if=none,format=qcow2,file="OpenCore.qcow2"
    -device ide-hd,bus=sata.1,drive=OpenCoreBoot,bootindex=1
    -drive id=MacHDD,if=none,file="SystemDisk.qcow2",format=qcow2
    -device ide-hd,bus=sata.2,drive=MacHDD,bootindex=2
    -netdev user,id=net0,hostfwd=tcp:0.0.0.0:0-:22
    -device virtio-net-pci,netdev=net0,id=net0,mac=52:54:00:c9:18:27

Run the new VM with::

    bypy vm run --with-gui `pwd`

Choose to boot from the SystemDisk at the OpenCore boot menu.

In Terminal.app mount the EFI partition (you can use diskutil list to get the partition device usually /dev/disk0)::

    sudo mkdir /Volumes/EFI
    sudo mount -t msdos /dev/disk0s1 /Volumes/EFI
    vim /Volumes/EFI/EFI/OC/config.plist

Set ShowPicker to false and Timeout to 5. Go to System Preferences->Startup
Disk and set the startup disk to the system disk. Click the Restart button.


After the OS is installed:

* enable automatic login for the ``kovid`` user in Preferences->Users->Login
  options

* turn on SSH, install vimrc and zshrc and ssh authorized_keys.

* System Preferences->Startup disk -> Set it to the correct disk (the one to
  which macOS was installed)

* Edit /etc/ssh/sshd_config and set the following to allow only key based login,
  UsePAM yes is needed to use ``screen``::

    PermitUserEnvironment yes
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    UsePAM yes

* Create the file ~/.ssh/environment::

    PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
    TERMINFO=/Users/kovid/.terminfo

* Copy over kitty terminfo using ssh kitten

* Turn off sleep, screensaver, auto-updates (system preferences->Energy saver,
  Screen saver and Lock Screen)

* Turn on TRIM so QEMU can recover disk space::

  sudo trimforce enable

* Change the hostname::

  sudo scutil --set HostName sonoma

* Update to macOS Sequoia using the in OS update facility (System
  settings->General->Software update). This takes about an hour, but works, it
  might hang on final reboot, in which case quit and restart the VM.

* Install Xcode from https://developer.apple.com/download/all/
Download the version of Xcode (12.4 for kitty and 15.4 for calibre) you need as a .xip archive. Run::

    curl -fSsL -O https://github.com/saagarjha/unxip/releases/download/v3.1/unxip && chmod +x unxip && \
    ./unxip -v Xco*.xip && mv Xco*.app /Applications && \
    sudo xcodebuild -license && \
    rm Xco*.xip && \
    python3 -m pip install certifi html5lib

* Install an up-to-date rsync::

    curl -L https://github.com/kovidgoyal/bypy/raw/master/virtual_machine/install_rsync_on_macos.sh | /bin/zsh /dev/stdin
