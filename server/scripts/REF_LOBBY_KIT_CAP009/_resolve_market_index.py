# -*- coding: utf-8 -*-
"""解析 mp/marketplace.json 后面那张 <索引, 指针> 表。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_48110000_0105A000.bin")
BASE = 0x48110000
TABLE_OFF = 0x3FED46


def main():
    b = open(P, "rb").read()
    print("本区 base=0x%08X size=%d" % (BASE, len(b)))
    print()
    print("解析 <u32 key, u32 ptr> 表, 从 0x%X 起:" % TABLE_OFF)
    off = TABLE_OFF
    n = 0
    while off + 8 <= len(b) and n < 30:
        key = struct.unpack_from("<I", b, off)[0]
        ptr = struct.unpack_from("<I", b, off + 4)[0]
        if not (BASE <= ptr < BASE + len(b)):
            print("  [%2d] key=0x%X ptr=0x%08X 越界, 停" % (n, key, ptr))
            break
        data = b[ptr - BASE:ptr - BASE + 64]
        txt = "".join(chr(c) if 32 <= c < 127 else "." for c in data)
        print("  [%2d] key=0x%-4X ptr=0x%08X | %s" % (n, key, ptr, txt))
        off += 8
        n += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
