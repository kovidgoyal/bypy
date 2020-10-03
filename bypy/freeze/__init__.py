#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import glob
import json
import marshal
import os
import shutil
from contextlib import suppress
from functools import lru_cache

from ..constants import PYTHON, iswindows, python_major_minor_version
from ..utils import run, walk
from .perfect_hash import get_c_code


@lru_cache()
def extension_suffixes():
    vals = run(
        PYTHON, '-c', 'from importlib.machinery import EXTENSION_SUFFIXES;'
        'import json;'
        'print(json.dumps(EXTENSION_SUFFIXES), end="")',
        get_output=True, library_path=True
    ).decode('utf-8')
    return sorted(
        map(str.lower, json.loads(vals)), key=len, reverse=True)


def compile_code(src, name):
    return run(
        PYTHON, '-c', f'''
import sys, marshal;
src = sys.stdin.buffer.read();
code = compile(src, "{name}", 'exec', optimize=2, dont_inherit=True)
sys.stdout.buffer.write(marshal.dumps(code))''',
        get_output=True, stdin=src, library_path=True)


def remove_extension_suffix(name):
    for q in extension_suffixes():
        if name.endswith(q):
            return name[:-len(q)]
    return name


def extract_extension_modules(src_dir, dest_dir, move=True):
    ext_map = {}

    def extract_extension(path, root):
        relpath = os.path.relpath(path, root)
        package, module = os.path.split(relpath)
        package = package.replace(os.sep, '/').replace('/', '.')
        module = remove_extension_suffix(module)
        fullname = package + ('.' if package else '') + module
        dest_name = fullname + extension_suffixes()[-1]
        ext_map[fullname] = dest_name
        dest = os.path.join(dest_dir, dest_name)
        if os.path.exists(dest):
            raise ValueError(
                f'Cannot extract {fullname} into {dest_dir}, it already exists'
            )
        if move:
            os.rename(path, dest)
        else:
            shutil.copy2(path, dest)
        bname, ext = dest.rpartition('.')[::2]
        bpy = bname + '.py'
        if os.path.exists(bpy):
            with open(bpy, 'rb') as f:
                raw = f.read().strip().decode('utf-8')
            if (not raw.startswith('def __bootstrap__')
                    or not raw.endswith('__bootstrap__()')):
                raise ValueError('The file %r has non bootstrap code' % bpy)
        for ext in ('', 'c', 'o'):
            with suppress(FileNotFoundError):
                os.remove(bpy + ext)

    def is_extension_module(x):
        q = x.lower()
        for c in extension_suffixes():
            if q.endswith(c):
                return True
        return False

    def find_pyds(base):
        for dirpath, dirnames, filenames in os.walk(base):
            for fname in filenames:
                if is_extension_module(fname):
                    yield os.path.join(dirpath, fname)

    def process_root(root, base=None):
        for path in find_pyds(root):
            extract_extension(path, base or root)

    def absp(x):
        return os.path.normcase(os.path.abspath(os.path.join(src_dir, x)))

    roots = {absp('lib-dynload')}
    for pth in glob.glob(os.path.join(src_dir, '*.pth')):
        for line in open(pth).readlines():
            line = line.strip()
            if line and not line.startswith('#') and os.path.exists(
                    os.path.join(src_dir, line)):
                roots.add(absp(line))

    for x in os.listdir(src_dir):
        x = absp(x)
        if x in roots:
            process_root(x)
        elif os.path.isdir(x):
            process_root(x, src_dir)
        elif is_extension_module(x):
            extract_extension(x, src_dir)
    return ext_map


def collect_files_for_internment(base):
    ans = {}
    for path in walk(base):
        name = os.path.relpath(path, base).replace(os.sep, '/')
        if '__pycache__/' not in name:
            ans[name] = path
    return {name: ans[name] for name in sorted(
        ans, key=lambda x: x.encode('utf-8'))}


def as_tree(items, extensions_map):
    root = {}
    for item in items:
        parts = item.split('/')
        parent = root
        for q in parts:
            parent = parent.setdefault(q, {})
    return marshal.dumps((root, extensions_map))


def cleanup_site_packages(sp_dir):
    bad_exts = {
        'exe', 'dll', 'lib', 'bat', 'pyi', 'pth', 'sip',
        'h', 'c', 'hpp', 'cpp', 'chm',
    }
    j = os.path.join
    for dirpath, dirnames, filenames in os.walk(sp_dir):
        allowed_dirs = {
            x for x in dirnames if
            x not in ('__pycache__',) and not x.endswith('.egg-info') and
            not x.endswith('.dist-info')
        }
        for remove in set(dirnames) - allowed_dirs:
            shutil.rmtree(os.path.join(dirpath, remove))
        dirnames[:] = list(allowed_dirs)
        for x in filenames:
            ext = x.rpartition('.')[2].lower()
            if ext in bad_exts:
                os.remove(os.path.join(dirpath, x))

    # remove some known useless dirs
    for x in (
        'calibre/manual', 'calibre/plugins', 'pythonwin', 'Crypto/SelfTest'
    ):
        deld = j(sp_dir, x)
        if os.path.exists(deld):
            shutil.rmtree(deld)
    # calibre needs only py files in frozen builds
    for f in walk(j(sp_dir, 'calibre')):
        if not f.endswith('.py'):
            os.remove(f)

    if not iswindows:
        return {}

    # special handling for win32
    os.rmdir(j(sp_dir, 'pywin32_system32'))
    wl = os.path.join(sp_dir, 'win32', 'lib')
    for x in os.listdir(wl):
        os.rename(os.path.join(wl, x), os.path.join(sp_dir, x))
    os.rmdir(wl)
    wl = os.path.dirname(wl)
    for x in os.listdir(wl):
        f = os.path.join(wl, x)
        if not os.path.isdir(f):
            os.rename(f, os.path.join(sp_dir, x))
    shutil.rmtree(wl)

    # Fix win32com
    comext = j(sp_dir, 'win32comext')
    shutil.copytree(j(comext, 'shell'), j(sp_dir, 'win32com', 'shell'))
    shutil.rmtree(comext)

    # Fix pycryptodome
    with open(j(sp_dir, 'Crypto', 'Util', '_file_system.py'), 'w') as fspy:
        fspy.write('''
import os, sys
def pycryptodome_filename(dir_comps, filename):
    base = os.path.join(sys.app_dir, 'app', 'bin')
    path = os.path.join(base, '.'.join(dir_comps + [filename]))
    return path
''')
    pyver = ''.join(map(str, python_major_minor_version()))
    return {
        'pywintypes': f'pywintypes{pyver}.dll',
        'pythoncom': f'pythoncom{pyver}.dll'
    }


def freeze_python(
    base, dest_dir, include_dir, extensions_map, develop_mode_env_var=''
):
    files = collect_files_for_internment(base)
    frozen_file = os.path.join(dest_dir, 'python-lib.bypy.frozen')
    index_data = {}
    with open(frozen_file, 'wb') as frozen_file:
        for name, path in files.items():
            raw = open(path, 'rb').read()
            index_data[name] = frozen_file.tell(), len(raw)
            frozen_file.write(raw)
    # from pprint import pprint
    # pprint(index_data)
    if len(index_data) > 9999:
        raise ValueError(
            'Too many files in python-lib have to switch'
            ' hash function to IntSaltHash and change C'
            ' template accordingly.')
    perfect_hash, code_to_get_index = get_c_code(index_data)
    values = []
    for k in sorted(index_data.keys(), key=perfect_hash):
        v = index_data[k]
        values.append(f'{{ {v[0]}u, {v[1]}u }}')
    vals = ','.join(values)
    tree = '\n'.join(bin_to_c(as_tree(index_data.keys(), extensions_map)))
    header = code_to_get_index + f'''
static void
get_value_for_hash_index(int index, unsigned long *offset, unsigned long *size)
{{
    typedef struct {{ unsigned long offset, size; }} Item;
    static const Item values[{len(values)}] = {{ {vals} }};
    if (index >= 0 && index < {len(values)}) {{
       *offset = values[index].offset; *size = values[index].size;
    }} else {{
    *offset = 0; *size = 0;
    }}
}}
static const char filesystem_tree[] = {{ {tree} }};
'''
    with open(os.path.join(include_dir, 'bypy-data-index.h'), 'w') as f:
        f.write(header)
    save_importer_src_to_header(include_dir, develop_mode_env_var)


def path_to_freeze_dir():
    return os.path.dirname(os.path.abspath(__file__))


def bin_to_c(src):
    if isinstance(src, str):
        src = src.encode('utf-8') + b'\0'
    src = bytearray(src)
    last = len(src) - 1

    line = []
    for i, byte in enumerate(src):
        line.append(str(byte))
        if i != last:
            line.append(',')
        if len(line) > 256:
            yield ''.join(line)
            line = []
    if line:
        yield ''.join(line)


def save_importer_src_to_header(dir_path, develop_mode_env_var):
    src = open(os.path.join(path_to_freeze_dir(), 'importer.py')).read()
    src = src.replace(
        '__DEVELOP_MODE_ENV_VAR__', repr(develop_mode_env_var), 1)
    src = src.replace(
        '__EXTENSION_SUFFIXES__', repr(extension_suffixes()), 1)
    src = compile_code(src, "bypy-importer.py")
    with open(os.path.join(dir_path, 'bypy-importer.h'), 'w') as f:
        script = '\n'.join(bin_to_c(src))
        print('static const char importer_script[] = {', script, '};', file=f)
