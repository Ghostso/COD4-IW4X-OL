"""Dump the two vtables that matter for the CODOL connect chain.

  objA        vtable 0xD59A7C
  HTTP client vtable 0xD95600

Read-only.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ch_dis import IMAGE_BASE, load_image  # noqa: E402


def dump(name, va, count):
    img = load_image()
    print("== %s vtable 0x%08X ==" % (name, va))
    for i in range(count):
        off = va - IMAGE_BASE + i * 4
        val = struct.unpack_from("<I", img, off)[0]
        print("  +0x%02X  0x%08X" % (i * 4, val))


def main():
    dump("objA", 0xD59A7C, 0x30)
    dump("HTTP-client", 0xD95600, 0x1C)


if __name__ == "__main__":
    main()
