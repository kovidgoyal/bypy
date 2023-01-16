First we need to create the installer image, this must be done on an existing macOS machine::

    git clone https://github.com/kholia/OSX-KVM.git && cd OSX-KVM/scripts/bigsur
    make BigSur-full.img

Now on the Linux machine::

    git clone https://github.com/kholia/OSX-KVM.git && cd OSX-KVM
    scp macos-machine:OSX-KVM/scripts/bigsur/BigSur-full.img ./BaseSystem.img
    qemu-img create -f qcow2 mac_hdd_ng.img 240G
    echo 1 | sudo tee /sys/module/kvm/parameters/ignore_msrs
    ./OpenCore-Boot.sh

Install the OS:

* Create a single HFS+ (macOS Extended Journalled) partition to install to

* Create a user account named: ``kovid`` during OS installation

Run::

    mkdir macos-bigsur
    mv mac_hdd_ng.img macos-bigsur/SystemDisk.qcow2
    cp OVMF*.fd macos-bigsur/
    cp OpenCore/OpenCore.qcow2 macos-bigsur/
    cd macos-bigsur

Create the following run.sh based on OpenCore-Boot.sh::

    #!/usr/bin/env bash
    args=(
    -smp 4,cores=2,sockets=1
    -m "4G"
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
    -drive id=OpenCoreBoot,if=none,snapshot=on,format=qcow2,file="OpenCore.qcow2"
    -device ide-hd,bus=sata.2,drive=OpenCoreBoot
    -drive id=MacHDD,if=none,file="SystemDisk.qcow2",format=qcow2
    -device ide-hd,bus=sata.3,drive=MacHDD
    -nic user,model=virtio-net-pci,mac=52:54:00:0e:0d:20,hostfwd=tcp:0.0.0.0:0-:22
    -monitor stdio
    -device VGA,vgamem_mb=128
    )

    qemu-system-x86_64 "${args[@]}"

Also, copy all the lines in args above into a file machine-spec stopping before the monitor line::

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
    -drive id=OpenCoreBoot,if=none,snapshot=on,format=qcow2,file="OpenCore.qcow2"
    -device ide-hd,bus=sata.2,drive=OpenCoreBoot
    -drive id=MacHDD,if=none,file="SystemDisk.qcow2",format=qcow2
    -device ide-hd,bus=sata.3,drive=MacHDD
    -nic user,model=virtio-net-pci,mac=52:54:00:0e:0d:20,hostfwd=tcp:0.0.0.0:0-:22

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
    ChallengeResponseAuthentication no
    UsePAM yes

* Create the file ~/.ssh/environment::

    PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
    TERMINFO=/Users/kovid/.terminfo

* Copy over kitty terminfo using ssh kitten

* Turn off sleep, screensaver, auto-updates.

* Install Xcode from https://developer.apple.com/download/more/
Download the version of Xcode (12.4 for kitty and 13.2.1 for calibre) you need as a .xip archive. Run::

    open Xcode*.xip
    mv Xco*.app /Applications
    sudo xcodebuild -license

* Install an up-to-date rsync::

    curl -L https://github.com/kovidgoyal/bypy/raw/master/virtual_machine/install_rsync_on_macos.sh | /bin/zsh /dev/stdin
