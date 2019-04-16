#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2019, Kovid Goyal <kovid at kovidgoyal.net>

import os
from operator import itemgetter

from .constants import PKG, PREFIX
from .download_sources import download, read_deps
from .utils import ensure_clear_dir, lcopy


def unbuilt(dep):
    return not os.path.exists(os.path.join(PKG, dep['name']))


def install_package(pkg_path, dest_dir):
    for dirpath, dirnames, filenames in os.walk(pkg_path):
        for x in tuple(dirnames):
            d = os.path.join(dirpath, x)
            if os.path.islink(d):
                filenames.append(x)
                dirnames.remove(x)
                continue
            name = os.path.relpath(d, pkg_path)
            os.makedirs(os.path.join(dest_dir, name), exist_ok=True)
        for x in filenames:
            f = os.path.join(dirpath, x)
            name = os.path.relpath(f, pkg_path)
            lcopy(f, os.path.join(dest_dir, name))


def install_packages(which_deps):
    ensure_clear_dir(PREFIX)


def init_env(which_deps=None):
    if which_deps is None:
        which_deps = read_deps()
    install_packages(which_deps)


def accept_func_from_names(names):
    names = frozenset(names)

    def accept(dep):
        return dep['name'] in names
    return accept


def main(parsed_args):
    accept_func = unbuilt
    all_deps = read_deps()
    all_dep_names = frozenset(map(itemgetter('name'), all_deps))
    if parsed_args.deps:
        accept_func = accept_func_from_names
        if frozenset(parsed_args.deps) - all_dep_names:
            raise SystemExit('Unknown dependencies: {}'.format(
                frozenset(parsed_args.deps) - all_dep_names))
    # pythonq = frozenset(python_deps).__contains__
    deps_to_build = tuple(filter(accept_func, all_deps))
    if not deps_to_build:
        raise SystemExit('No buildable deps were specified')
    names_of_deps_to_build = frozenset(map(itemgetter('name'), deps_to_build))
    other_deps = [
        dep for dep in all_deps if dep['name'] not in names_of_deps_to_build]
    init_env(other_deps)
    download(deps_to_build)
