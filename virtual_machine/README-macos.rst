First we need to create the installer image, this must be done on an existing macOS machine::

    git clone https://github.com/kholia/OSX-KVM.git && cd OSX-KVM
    ./fetch-macOS-v2.py (choose Ventura)

Now on the Linux machine::

    git clone https://github.com/kholia/OSX-KVM.git && cd OSX-KVM
    scp macos-machine:OSX-KVM/BaseSystem.dmg .
    dmg2img -i BaseSystem.dmg BaseSystem.img
    qemu-img create -f qcow2 mac_hdd_ng.img 240G
    echo 1 | sudo tee /sys/module/kvm/parameters/ignore_msrs
    ./OpenCore-Boot.sh

Install the OS:


* Run Disk Utility and create a single HFS+ (macOS Extended Journalled) partition to install to

* Create a user account named: ``kovid`` during OS installation

Run::

    mkdir macos-ventura
    mv mac_hdd_ng.img macos-ventura/SystemDisk.qcow2
    cp OVMF*.fd macos-ventura/
    cp OpenCore/OpenCore.qcow2 macos-ventura/
    cd macos-ventura

Create the following :file:`machine-spec` file based on OpenCore-Boot.sh::

    # Processors
    -smp 4,cores=2,sockets=1
    # RAM
    -m 4G

    -enable-kvm
    -cpu Penryn,kvm=on,vendor=GenuineIntel,+invtsc,vmware-cpuid-freq=on,+ssse3,+sse4.2,+popcnt,+avx,+aes,+xsave,+xsaveopt,check
    -machine q35
    -usb -device usb-kbd -device usb-tablet
    -device usb-ehci,id=ehci
    -device nec-usb-xhci,id=xhci
    -global nec-usb-xhci.msi=off
    -device isa-applesmc,osk="ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"
    -drive if=pflash,format=raw,readonly=on,file="OVMF_CODE.fd"
    -drive if=pflash,format=raw,file="OVMF_VARS-1024x768.fd"
    -smbios type=2
    -device ich9-intel-hda -device hda-duplex
    -device ich9-ahci,id=sata
    -drive id=OpenCoreBoot,if=none,format=qcow2,file="OpenCore.qcow2"
    -device ide-hd,bus=sata.1,drive=OpenCoreBoot
    -drive id=MacHDD,if=none,file="SystemDisk.qcow2",format=qcow2
    -device ide-hd,bus=sata.2,drive=MacHDD
    -nic user,model=virtio-net-pci,mac=52:54:00:0e:0d:20,hostfwd=tcp:0.0.0.0:0-:22

Run the new VM with::

    bypy vm run --with-gui `pwd`

Choose to boot from the SystemDisk at the OpenCore boot menu.

In Terminal.app mount the EFI partition (you can use diskutil list to get the partition device)::

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

* Turn off sleep, screensaver, auto-updates.

* Change the hostname to ventura

* Install Xcode from https://developer.apple.com/download/more/
Download the version of Xcode (12.4 for kitty and 15 for calibre) you need as a .xip archive. Run::

    open Xcode*.xip
    mv Xco*.app /Applications
    sudo xcodebuild -license

* Install an up-to-date rsync::

    curl -L https://github.com/kovidgoyal/bypy/raw/master/virtual_machine/install_rsync_on_macos.sh | /bin/zsh /dev/stdin
