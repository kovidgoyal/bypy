Create a VM using https://github.com/foxlet/macOS-Simple-KVM

After the OS is installed:

* turn on SSH, change shell to zsh, install vimrc and zshrc and ssh authorized_keys.

* Copy over kitty terminfo using ssh kitten

* Turn off sleep, screensaver, auto-updates.

* Mount the EFI partition that contains
the clover bootloader, look for config.plist and change DracoHD
to LastBootedVolume. You can also decrease the timeout if you prefer.
