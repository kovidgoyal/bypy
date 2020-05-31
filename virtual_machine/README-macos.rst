Create a VM using https://github.com/foxlet/macOS-Simple-KVM
With a SystemDisk::

    qemu-img create -f qcow2 SystemDisk.qcow2 240G

Create a user account named: kovid

After the OS is installed:

* Change the two network related lines in the launch script, which use an obsolete
  syntax to::

    -nic user,model=e1000-82545em,mac=52:54:00:0e:0d:20,hostfwd=tcp:0.0.0.0:22001-:22

* Change the number of CPUS and RAM to::

    -smp 4,cores=2
    -m 4G

* turn on SSH, change shell to zsh, install vimrc and zshrc and ssh authorized_keys.

* Edit /etc/ssh/sshd_config and set the following to allow only key based login::

    PasswordAuthentication no
    ChallengeResponseAuthentication no
    UsePAM no

* Copy over kitty terminfo using ssh kitten

* Turn off sleep, screensaver, auto-updates.

* Mount the EFI partition that contains
the clover bootloader, look for config.plist and change DracoHD
to LastBootedVolume. You can also decrease the timeout if you prefer.
