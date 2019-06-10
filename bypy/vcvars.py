#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import ctypes.wintypes
import os
import subprocess
from functools import lru_cache

CSIDL_PROGRAM_FILES = 38
CSIDL_PROGRAM_FILESX86 = 42


@lru_cache()
def get_program_files_location(which=CSIDL_PROGRAM_FILESX86):
    SHGFP_TYPE_CURRENT = 0
    buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(0, CSIDL_PROGRAM_FILESX86, 0,
                                           SHGFP_TYPE_CURRENT, buf)
    return buf.value


def find_vs2017():
    for which in (CSIDL_PROGRAM_FILESX86, CSIDL_PROGRAM_FILES):
        root = get_program_files_location(which)
        vswhere = os.path.join(root, "Microsoft Visual Studio", "Installer",
                               "vswhere.exe")
        if not os.path.exists(vswhere):
            continue
        path = subprocess.check_output([
            vswhere,
            "-latest",
            "-prerelease",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
            "-products",
            "*",
        ],
                                       encoding="mbcs",
                                       errors="strict").strip()
        return os.path.join(path, "VC", "Auxiliary", "Build")
    raise SystemExit('Could not find VisualStudio 2017')


def find_vcvarsall(version=15.0):
    productdir = find_vs2017()
    vcvarsall = os.path.join(productdir, "vcvarsall.bat")
    if os.path.isfile(vcvarsall):
        return vcvarsall
    raise SystemExit("Unable to find vcvarsall.bat in productdir: " +
                     productdir)


def remove_dups(variable):
    old_list = variable.split(os.pathsep)
    new_list = []
    for i in old_list:
        if i not in new_list:
            new_list.append(i)
    return os.pathsep.join(new_list)


def query_process(cmd, is64bit):
    if is64bit and 'PROGRAMFILES(x86)' not in os.environ:
        os.environ['PROGRAMFILES(x86)'] = get_program_files_location()
    result = {}
    popen = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    try:
        stdout, stderr = popen.communicate()
        if popen.wait() != 0:
            raise RuntimeError(stderr.decode("mbcs"))

        stdout = stdout.decode("mbcs")
        for line in stdout.splitlines():
            if '=' not in line:
                continue
            line = line.strip()
            key, value = line.split('=', 1)
            key = key.lower()
            if key == 'path':
                if value.endswith(os.pathsep):
                    value = value[:-1]
                value = remove_dups(value)
            result[key] = value

    finally:
        popen.stdout.close()
        popen.stderr.close()
    return result


def query_vcvarsall(is64bit=True):
    plat = 'amd64' if is64bit else 'amd64_x86'
    vcvarsall = find_vcvarsall()
    env = query_process('"%s" %s & set' % (vcvarsall, plat), is64bit)

    def g(k):
        try:
            return env[k]
        except KeyError:
            return env[k.lower()]

    return {
        k: g(k)
        for k in ('PATH LIB INCLUDE LIBPATH WINDOWSSDKDIR'
                  ' VS150COMNTOOLS UCRTVERSION UNIVERSALCRTSDKDIR').split()
    }
