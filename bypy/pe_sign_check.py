#!/usr/bin/env python
# License: GPLv3 Copyright: 2025, Kovid Goyal <kovid at kovidgoyal.net>

import os
import struct
import sys
from ctypes import wintypes

# --- Constants ---
IMAGE_DIRECTORY_ENTRY_SECURITY = 4
PE32_MAGIC = 0x10b
PE32PLUS_MAGIC = 0x20b


def has_signature(file_path: str) -> bool:
    """
    Robustly and quickly checks if a PE file contains a digital signature
    block by parsing the PE header and checking if the image signature block
    exists and has a non-zero size. Returns False on any parsing error.
    """
    with open(file_path, 'rb') as f:
        if f.read(2) != b'MZ':
            return False
        f.seek(60)
        try:
            e_lfanew, = struct.unpack('<I', f.read(4))
        except Exception:
            return False

        # PE Header
        f.seek(e_lfanew)
        if f.read(4) != b'PE\0\0':
            return False

        # 4. Optional Header and Data Directories
        f.seek(20, os.SEEK_CUR)
        optional_header_start = f.tell()
        f.seek(optional_header_start)
        magic = wintypes.WORD.from_buffer_copy(f.read(2)).value
        f.seek(optional_header_start)

        if magic == PE32_MAGIC:
            f.seek(92, os.SEEK_CUR)
        elif magic == PE32PLUS_MAGIC:
            f.seek(108, os.SEEK_CUR)
        else:
            return False
        try:
            num, = struct.unpack('<I', f.read(4))
        except Exception:
            return False
        if num <= IMAGE_DIRECTORY_ENTRY_SECURITY:
            return False

        # The data directories immediately follow the optional header
        sizeof_image_data_directory = 8
        f.seek(sizeof_image_data_directory * IMAGE_DIRECTORY_ENTRY_SECURITY + 4, os.SEEK_CUR)
        try:
            size, = struct.unpack('<I', f.read(4))
        except Exception:
            return False
        return size > 0


def check_all_files_in_folder_are_signed(path: str) -> None:
    rc = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fpath = os.path.join(dirpath, f)
            if f.rpartition('.')[-1].lower() in ('exe', 'pyd', 'dll') and not has_signature(fpath):
                print('Unsigned:', fpath, file=sys.stderr)
                rc = 1
    raise SystemExit(rc)



if __name__ == '__main__':
    if os.path.isdir(sys.argv[-1]):
        check_all_files_in_folder_are_signed(sys.argv[-1])
    else:
        print(sys.argv[-1], 'has signature' if has_signature(sys.argv[-1]) else 'is not signed')
