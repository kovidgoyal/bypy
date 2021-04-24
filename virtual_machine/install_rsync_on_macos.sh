#!/bin/zsh
#
# install_rsync_on_macos.sh
# Copyright (C) 2020 Kovid Goyal <kovid at kovidgoyal.net>
#
# Distributed under terms of the GPLv3 license.

# see https://github.com/Homebrew/homebrew-core/blob/master/Formula/rsync.rb::
set -e
set -x
set -o pipefail
VERSION=3.2.3
cd
rm -rf build-rsync && mkdir build-rsync && cd build-rsync
curl -L -O https://download.samba.org/pub/rsync/src/rsync-$VERSION.tar.gz
curl -L -O https://download.samba.org/pub/rsync/src/rsync-patches-$VERSION.tar.gz
tar xvf rsync-$VERSION.tar.gz
tar xvf rsync-pat*
cd rsync-$VERSION
patch -p1 <patches/fileflags.diff
./prepare-source
./configure --disable-debug --enable-ipv6 --disable-openssl --disable-xxhash --disable-zstd --disable-lz4 --prefix=/usr
make -j4
sudo mkdir -p /usr/local/bin
sudo cp rsync /usr/local/bin/rsync
sudo chmod +x /usr/local/bin/rsync
cd && rm -rf build-rsync
