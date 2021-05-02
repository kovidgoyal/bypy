These instructions are loosely based off https://futurewei-cloud.github.io/ARM-Datacenter/qemu/how-to-launch-aarch64-vm/
# Preparing for qemu install

```sh
apt-get install qemu-system-arm
apt-get install qemu-efi-aarch64
apt-get install qemu-utils
```

```bash
dd if=/dev/zero of=flash1.img bs=1M count=64
dd if=/dev/zero of=flash0.img bs=1M count=64
dd if=/usr/share/qemu-efi-aarch64/QEMU_EFI.fd of=flash0.img conv=notrunc

wget https://dl-cdn.alpinelinux.org/alpine/v3.13/releases/aarch64/alpine-virt-3.13.5-aarch64.iso -O alpine-aarch64.iso
qemu-img create -f qcow2 alpine.qcow2

```

# Start qemu installation

```bash
qemu-system-aarch64 -nographic -machine virt,gic-version=max -m 512M -cpu max -smp 4 \
-netdev user,id=vnet,hostfwd=:127.0.0.1:0-:22 -device virtio-net-pci,netdev=vnet \
-drive file=alpine.qcow2,if=none,id=drive0,cache=writeback -device virtio-blk,drive=drive0,bootindex=0 \
-drive file=alpine-aarch64.iso,if=none,id=drive1,cache=writeback -device virtio-blk,drive=drive1,bootindex=1 \
-drive file=flash0.img,format=raw,if=pflash -drive file=flash1.img,format=raw,if=pflash 
```

# OS Installation automation
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
#PROXYOPTS="http://webproxy:8080"
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


# Booting image
```
qemu-system-aarch64 -nographic -machine virt,gic-version=max -m 512M -cpu max -smp 4 \
-netdev user,id=vnet,hostfwd=:127.0.0.1:0-:22 -device virtio-net-pci,netdev=vnet \
-drive file=alpine.qcow2,if=none,id=drive0,cache=writeback -device virtio-blk,drive=drive0,bootindex=0 \
-drive file=flash0.img,format=raw,if=pflash -drive file=flash1.img,format=raw,if=pflash 
```
