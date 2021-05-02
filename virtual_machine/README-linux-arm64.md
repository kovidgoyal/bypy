These instructions are loosely based off https://futurewei-cloud.github.io/ARM-Datacenter/qemu/how-to-launch-aarch64-vm/
# Preparing host for qemu install

```sh
apt-get install qemu-system-arm
apt-get install qemu-efi-aarch64
apt-get install qemu-utils
```

```bash
dd if=/dev/zero of=flash1.img bs=1M count=64
dd if=/dev/zero of=flash0.img bs=1M count=64
dd if=/usr/share/qemu-efi-aarch64/QEMU_EFI.fd of=flash0.img conv=notrunc

#for alpine
wget https://dl-cdn.alpinelinux.org/alpine/v3.13/releases/aarch64/alpine-virt-3.13.5-aarch64.iso -O alpine-arm64.iso
#for ubuntu xenial
wget http://ports.ubuntu.com/ubuntu-ports/dists/xenial-updates/main/installer-arm64/current/images/netboot/mini.iso -O xenial-arm64.iso

qemu-img create -f qcow2 linux-arm64.qcow2 16G

```

# Start qemu installation

```bash
#Change `xenial-arm64.iso to the alpine one if you want`
qemu-system-aarch64 -nographic -machine virt,gic-version=max -m 1024M -cpu max -smp 4 \
-nic user,model=virtio-net-pci,hostfwd=tcp:0.0.0.0:22003-:22 \
-drive file=linux-arm64.qcow2,if=none,id=drive0,cache=writeback -device virtio-blk,drive=drive0,bootindex=0 \
-drive file=xenial-arm64.iso,if=none,id=drive1,cache=writeback -device virtio-blk,drive=drive1,bootindex=1 \
-drive file=flash0.img,format=raw,if=pflash -drive file=flash1.img,format=raw,if=pflash 
```

# OS Installation

## Ubuntu xenial
Select `Advanced options -> automated installation` and paste `https://gist.githubusercontent.com/jdmichaud/863cd34739d0a3f3ab0588caa955f920/raw/1402edc32dee3f221151510c35d51258874df4ba/preseed` as the preseed location. You will then need to use `ubuntu`/`ubuntu` to log in.


## Alpine
You can attempt to automate the installer but honestly it takes ~10 minutes to run through. Ensure you're using the `sys` option while setting up the disk, and that your mirror actually works as some of the options are dead.
<details>
    
```bash
# log in with `root`

# Create answer file for installer (or make your own with setup-alpine -c answerfile)
cat > answerfile << EOF
# Use US layout with US variant
KEYMAPOPTS="us us"
# Set hostname to alpine-test
HOSTNAMEOPTS="-n alpine-test"
# Contents of /etc/network/interfaces
INTERFACESOPTS="auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
    hostname alpine-test
"
# Search domain of example.com, Google public nameserver
DNSOPTS="-d 8.8.8.8"
# Set timezone to UTC
TIMEZONEOPTS="-z UTC"
# set http/ftp proxy
PROXYOPTS="none"
# Add a random mirror
APKREPOSOPTS="-f"
# Install Openssh
SSHDOPTS="-c openssh"
# Use openntpd
NTPOPTS="-c openntpd"
# Use /dev/sda as a data disk
DISKOPTS="-m sys /dev/vda"
# Setup in /media/sdb1
#LBUOPTS="/media/sdb1"
#APKCACHEOPTS="/media/sdb1/cache"
EOF

# run setup with answerfile
setup-alpine -f answerfile
# !! You will still be asked for a new password for root. Choose `alpine`.
# You will need to manually confirm formatting of the disk
```

</details>

# Booting image
```
qemu-system-aarch64 -nographic -machine virt,gic-version=max -m 512M -cpu max -smp 4 \
-nic user,model=virtio-net-pci,hostfwd=tcp:0.0.0.0:22003-:22 \
-drive file=alpine.qcow2,if=none,id=drive0,cache=writeback -device virtio-blk,drive=drive0,bootindex=0 \
-drive file=flash0.img,format=raw,if=pflash -drive file=flash1.img,format=raw,if=pflash
```
# Post-install guest OS modifications
## Allow root login in ssh config
```bash
sudo su
chpasswd #Change the root password
vi /etc/ssh/sshd_conf # Allow `rootpasswordlogin`
service sshd restart
```
You should then be able to ssh via `ssh root@localhost -p 22003`

## `glibc` 2.23 (alpine only)
This ensures that the glibc is old enough for the compiled bins to run without issues on images both young and old
```bash
apk add wget
wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://alpine-pkgs.sgerrand.com/sgerrand.rsa.pub
wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.23-r4/glibc-2.23-r4.apk
apk add glibc-2.23-r4.apk
```
## Add `kovid` user
```bash
adduser kovid
```
