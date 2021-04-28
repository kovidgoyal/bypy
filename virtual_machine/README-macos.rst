Create a VM using https://github.com/foxlet/macOS-Simple-KVM (for Catalina)
With a SystemDisk::

    qemu-img create -f qcow2 SystemDisk.qcow2 240G

Install the OS:

* Create a single HFS+ (dont know if APFS works well) partition to install to

* Create a user account named: ``kovid`` during OS installation

After the OS is installed:

* Change the two network related lines in the launch script, which use an obsolete
  syntax to::

    -nic user,model=e1000-82545em,mac=52:54:00:0e:0d:20,hostfwd=tcp:0.0.0.0:22001-:22

* Change the number of CPUS and RAM to::

    -smp 4,cores=2
    -m 4G

* enable automatic login for the ``kovid`` user in Preferences->Users->Login
  options

* turn on SSH, install vimrc and zshrc and ssh authorized_keys.

* Edit /etc/ssh/sshd_config and set the following to allow only key based login::

    PermitUserEnvironment yes
    PasswordAuthentication no
    ChallengeResponseAuthentication no
    UsePAM no

* Create the file ~/.ssh/environment::

    PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

* Copy over kitty terminfo using ssh kitten

* Turn off sleep, screensaver, auto-updates.

* Mount the EFI partition that contains
the clover bootloader, look for config.plist and change DracoHD
to LastBootedVolume. You can also decrease the timeout if you prefer::

    sudo mkdir /Volumes/efi
    sudo mount -t msdos /dev/disk0s1 /Volumes/efi
    sudo vim `find /Volumes/efi -iname config.plist`

* Install Xcode from https://developer.apple.com/download/more/
Download the version of Xcode (at least 12.4) you need as a .xip archive. Run::

    open Xcode*.xip
    mv Xco*.app /Applications
    sudo xcodebuild -license

* Install an up-to-date rsync::

    curl -L https://github.com/kovidgoyal/bypy/raw/master/virtual_machine/install_rsync_on_macos.sh | /bin/zsh /dev/stdin
