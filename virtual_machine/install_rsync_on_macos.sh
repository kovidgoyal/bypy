#!/bin/zsh
#
# install_rsync_on_macos.sh
# Copyright (C) 2020 Kovid Goyal <kovid at kovidgoyal.net>
#
# Distributed under terms of the GPLv3 license.

# see https://github.com/Homebrew/homebrew-core/blob/master/Formula/rsync.rb::
set -e
set -o pipefail
cd
mkdir build-rsync && cd build-rsync
curl -O https://download.samba.org/pub/rsync/src/rsync-3.1.3.tar.gz
curl -O https://download.samba.org/pub/rsync/src/rsync-patches-3.1.3.tar.gz
tar xvf rsync-3*
tar xvf rsync-pat*
cd rsync-*
patch -p1 <patches/fileflags.diff
patch -p1 <patches/hfs-compression.diff
curl https://raw.githubusercontent.com/Homebrew/formula-patches/344bf3b/rsync/fix-crtimes-patch-3.1.3.diff |patch -p1
./prepare-source
./configure --disable-debug --enable-ipv6 --prefix=/usr
make -j4
cat rsync | sudo tee /usr/bin/rsync > /dev/null
cd && rm -rf build-rsync

