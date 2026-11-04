#!/usr/bin/env python
# License: GPLv3 Copyright: 2026, Kovid Goyal <kovid at kovidgoyal.net>

from bypy.utils import cmake_build


def main(args):
    # Header only package, nothing is compiled, cmake just installs the
    # headers, the registry and the VulkanHeaders cmake config files
    cmake_build(
        VULKAN_HEADERS_ENABLE_TESTS='OFF',
        VULKAN_HEADERS_ENABLE_MODULE='OFF',
        VULKAN_HEADERS_ENABLE_INSTALL='ON',
        relocate_pkgconfig=False,
    )
