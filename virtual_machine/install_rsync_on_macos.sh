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
VERSION=3.1.3
cd
mkdir build-rsync && cd build-rsync
curl -L -O https://download.samba.org/pub/rsync/src/rsync-$VERSION.tar.gz
curl -L -O https://download.samba.org/pub/rsync/src/rsync-patches-$VERSION.tar.gz
tar xvf rsync-$VERSION.tar.gz
tar xvf rsync-pat*
cd rsync-$VERSION
patch -p1 <patches/fileflags.diff
patch -p1 <patches/crtimes.diff
curl -L https://raw.githubusercontent.com/Homebrew/formula-patches/344bf3b/rsync/fix-crtimes-patch-$VERSION.diff |patch -p1
./prepare-source
./configure --disable-debug --enable-ipv6 --prefix=/usr
make -j4
cat rsync | sudo tee /usr/bin/rsync > /dev/null
cd && rm -rf build-rsync

