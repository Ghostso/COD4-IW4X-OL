# -*- coding: utf-8 -*-
"""判断这些地址是模块内偏移还是绝对虚拟地址。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.abspath(os.path.join(ROOT, "..", "run_codol_001",
                                    "sandbox_datafix_20260929"))
FILES = ("codoMP_client_shipRetailBase.dll", "codoMP_client_shipRetail.exe")
TARGETS = (0x239B120, 0x1E2D338, 0xE5C8C0, 0x49D3B0, 0x4A9330, 0x483DB0)


def check(name):
    p = os.path.join(GAME, name)
    if not os.path.exists(p):
        print("missing %s" % name)
        return
    sz = os.path.getsize(p)
    print("%s: %d bytes (0x%X)" % (name, sz, sz))
    for t in TARGETS:
        if t < sz:
            print("    0x%08X IN file (remain 0x%X)" % (t, sz - t))
        else:
            print("    0x%08X OUT of file" % t)
    print()


def main():
    for n in FILES:
        check(n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
