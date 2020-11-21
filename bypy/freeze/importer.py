#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import marshal
import sys

import _imp
from _frozen_importlib import (ModuleSpec, _call_with_frames_removed,
                               _verbose_message)
from bypy_frozen_importer import (abspath, get_data_at, get_home_directory,
                                  getenv, index_for_name,
                                  initialize_data_access, mode_for_path,
                                  offsets_for_index, path_sep, print,
                                  read_file, setenv, windows_expandvars)

DEVELOP_MODE_ENV_VAR = __DEVELOP_MODE_ENV_VAR__  # noqa
PATH_TO_USER_ENV_VARS = __PATH_TO_USER_ENV_VARS__  # noqa
EXTENSION_SUFFIXES = __EXTENSION_SUFFIXES__  # noqa
py_ext = '.pyc'
path_separators = '\\/' if path_sep == '\\' else '/'


def _path_is_mode_type(path, mode):
    """Test whether the path is the specified mode type."""
    try:
        qmode = mode_for_path(path)
    except OSError:
        return False
    return (qmode & 0o170000) == mode


def _path_isfile(path):
    """Replacement for os.path.isfile."""
    return _path_is_mode_type(path, 0o100000)


def _path_isdir(path):
    """Replacement for os.path.isdir."""
    return _path_is_mode_type(path, 0o040000)


def _path_join(*path_parts):
    """Replacement for os.path.join()."""
    return path_sep.join([part.rstrip(path_separators)
                          for part in path_parts if part])


def _path_split(path):
    """Replacement for os.path.split()."""
    if len(path_separators) == 1:
        front, _, tail = path.rpartition(path_sep)
        return front, tail
    for x in reversed(path):
        if x in path_separators:
            front, tail = path.rsplit(x, maxsplit=1)
            return front, tail
    return '', path


def get_module_code(offset, size):
    data = get_data_at(offset, size)
    return marshal.loads(data)


def unix_expandvars(text):
    ans = []
    allowed_chars = \
        'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'

    while text:
        idx = text.find('$')
        if idx == -1:
            ans.append(text)
            break
        if len(text) == idx + 1:
            ans.append(text)
            break
        ans.append(text[:idx])
        text = text[idx:]
        extent = 0
        if text.startswith('${'):
            close_idx = text.find('}')
            if close_idx > 1:
                extent = close_idx
        else:
            for i, c in enumerate(text):
                if i == 0:
                    continue
                if c not in allowed_chars:
                    extent = i - 1
                    break
            else:
                if not extent and i > 0:
                    extent = i
        if extent:
            var = text[1:extent+1]
            if var.startswith('{'):
                var = var[1:-1]
            val = getenv(var) or text[:extent+1]
            ans.append(val)
            text = text[extent+1:]
        else:
            ans.append('$')
            text = text[1:]

    return ''.join(ans)


expandvars = windows_expandvars if path_sep == '\\' else unix_expandvars


class ExtensionFileLoader:

    def __init__(self, name, path):
        self.name = name
        self.path = path

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.__dict__ == other.__dict__)

    def __hash__(self):
        return hash(self.name) ^ hash(self.path)

    def create_module(self, spec):
        module = _call_with_frames_removed(_imp.create_dynamic, spec)
        _verbose_message(
            f'extension module {spec.name!r} loaded from {self.path!r}')
        return module

    def exec_module(self, module):
        _call_with_frames_removed(_imp.exec_dynamic, module)
        _verbose_message(
            'extension module {self.name!r} executed from {self.path!r}')

    def is_package(self, fullname):
        file_name = _path_split(self.path)[1]
        return any(file_name == '__init__' + suffix
                   for suffix in EXTENSION_SUFFIXES)

    def get_code(self, fullname):
        return None

    def get_source(self, fullname):
        return None

    def get_filename(self, fullname):
        """Return the path to the source file as found by the finder."""
        return self.path


class FrozenByteCodeLoader:

    __slots__ = (
        'name', 'offset', 'size', '_is_package', 'filesystem_tree',
        'resource_prefix', 'filename'
    )

    def __init__(
        self, fullname, offset, size, name,
        is_package, filesystem_tree, filename
    ):
        self.name = fullname
        self.offset, self.size = offset, size
        self._is_package = is_package
        self.filename = filename
        self.resource_prefix = name.split('.')[:-1]
        self.filesystem_tree = filesystem_tree

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__ and
            self.offset == other.offset
        )

    def __hash__(self):
        return hash(self.name) ^ hash(self.offset)

    def get_resource_reader(self, fullname=None):
        return self

    def create_module(self, spec):
        pass

    def get_code(self, fullname):
        return get_module_code(self.offset, self.size)

    def is_package(self, fullname):
        return self._is_package

    def get_source(self, fullname):
        return None

    def get_filename(self, fullname):
        return self.filename

    def exec_module(self, module):
        code = _call_with_frames_removed(
            get_module_code, self.offset, self.size)
        # PyQt needs __file__ otherwise importing fails
        module.__file__ = self.filename
        exec(code, module.__dict__)

    @property
    def node_for_self(self):
        p = self.filesystem_tree
        for part in self.resource_prefix:
            p = p[part]
        return p

    def contents(self):
        return tuple(self.node_for_self)

    def is_resource(self, name):
        children = self.node_for_self.get(name)
        if children is None or children:
            return False
        return True

    def resource_path(self, name):
        raise FileNotFoundError(
            f'{name} is not available as a filesystem path in frozen builds')

    def open_resource(self, name):
        q = '/'.join(self.resource_prefix) + '/' + name
        idx = index_for_name(q)
        if idx < 0:
            raise FileNotFoundError(
                f'{name} is not present in {self.name}')
        import io
        offset, size = offsets_for_index(idx)
        return io.BytesIO(get_data_at(offset, size))


def expanduser(path):
    if not path.startswith('~'):
        return path
    home = get_home_directory()
    for x in path_separators:
        home.rstrip(x)
    if not home:
        return path
    if path == '~':
        return home
    if path[1:2] not in path_separators:
        return path
    return home + path_sep + path[2:]


def read_user_env_vars():
    path = expanduser(PATH_TO_USER_ENV_VARS)
    try:
        raw = read_file(path).decode('utf-8', 'replace')
    except FileNotFoundError:
        return
    for line in raw.splitlines():
        if line.startswith('#'):
            continue
        parts = line.split('=', 1)
        if len(parts) == 2:
            key, val = parts
            val = expandvars(expanduser(val))
            setenv(key, val)


class BypyFrozenImporter:

    def __init__(self):
        self.libdir = libdir  # noqa
        self.dataloc = _path_join(self.libdir, 'python-lib.bypy.frozen')
        self.filesystem_tree, self.extensions_map = marshal.loads(
            initialize_data_access(self.dataloc))
        self.develop_mode_path = None
        if PATH_TO_USER_ENV_VARS:
            try:
                read_user_env_vars()
            except Exception as err:
                print(
                    'Failed to read environment variables from:',
                    PATH_TO_USER_ENV_VARS, 'with error:', str(err))
        dv = getenv(DEVELOP_MODE_ENV_VAR) if DEVELOP_MODE_ENV_VAR else None
        if dv and _path_isdir(dv):
            self.develop_mode_path = abspath(dv)

    def __repr__(self):
        return f'{self.__class__.__name__} with data in {self.libdir}'

    def index_for_python_name(self, name):
        return index_for_name(name.replace('.', '/') + py_ext)

    def is_package(self, fullname):
        return self.index_for_python_name(fullname + '.__init__') > -1

    def find_spec(self, fullname, path, target=None):
        ext_dest_name = self.extensions_map.get(fullname)
        if ext_dest_name is not None:
            ext_path = _path_join(self.libdir, ext_dest_name)
            return ModuleSpec(
                fullname, ExtensionFileLoader(fullname, ext_path),
                origin=ext_path, is_package=False)
        if self.develop_mode_path:
            ans = self.find_spec_in_develop_mode(fullname, path, target=None)
            if ans is not None:
                return ans
        package_name = fullname + '.__init__'
        package_idx = self.index_for_python_name(package_name)
        is_package = package_idx > -1
        if is_package:
            name = package_name
            idx = package_idx
        else:
            name = fullname
            idx = self.index_for_python_name(name)

        if is_package or idx > -1:
            offset, size = offsets_for_index(idx)
            fpath = self.dataloc + path_sep
            filename = fpath + name.replace('.', path_sep) + py_ext
            return ModuleSpec(
                fullname, FrozenByteCodeLoader(
                    fullname, offset, size, name, is_package,
                    self.filesystem_tree, filename
                ), origin=filename, is_package=is_package
            )

    def find_spec_in_develop_mode(self, fullname, path, target=None):
        base = _path_join(self.develop_mode_path, *fullname.split('.'))
        package_path = _path_join(base, '__init__.py')
        is_package = _path_isfile(package_path)
        full_path = package_path if is_package else (base + '.py')
        if is_package or _path_isfile(full_path):
            from _frozen_importlib_external import spec_from_file_location
            return spec_from_file_location(fullname, location=full_path)


importer = BypyFrozenImporter()
sys.meta_path.insert(0, importer)


def running_in_develop_mode():
    return importer.develop_mode_path is not None
