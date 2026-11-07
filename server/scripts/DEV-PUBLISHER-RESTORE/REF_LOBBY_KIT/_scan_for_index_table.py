# -*- coding: utf-8 -*-
"""在 r_48110000 区里找 <u32 key, u32 ptr> 索引表。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_48110000_0105A000.bin")
BASE = 0x48110000


def main():
    b = open(P, "rb").read()
    size = len(b)
    print("base=0x%08X size=0x%X" % (BASE, size))
    best = []
    off = 0x3FE000
    while off < min(size - 64, 0x402000):
        ok = 0
        for k in range(8):
            ptr = struct.unpack_from("<I", b, off + k * 8 + 4)[0]
            if BASE <= ptr < BASE + size:
                ok += 1
        if ok >= 8:
            best.append((off, struct.unpack_from("<I", b, off)[0]))
        off += 4
    print("连续 8 对的起点 %d 个:" % len(best))
    for o, first in best[:20]:
        print("  0x%X 首 key=0x%X" % (o, first))
    return 0


if __name__ == "__main__":
    sys.exit(main())
