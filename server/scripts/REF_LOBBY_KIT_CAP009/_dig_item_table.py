# -*- coding: utf-8 -*-
"""深挖 r_48110000_0105A000.bin 里 mp/item_cnc.csv 附近的结构。

目标: 找出 item 表的行格式(尤其 itemID 在哪)。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_48110000_0105A000.bin")


def main():
    b = open(P, "rb").read()
    print("文件 %d 字节" % len(b))
    i = b.find(b"mp/item_cnc.csv")
    print("mp/item_cnc.csv @0x%X" % i)
    print()
    # 前后 0x600 字节的原始 hex + ascii
    lo = max(0, i - 0x200)
    hi = min(len(b), i + 0x600)
    for o in range(lo, hi, 16):
        chunk = b[o:o + 16]
        hexs = " ".join("%02X" % c for c in chunk)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        mark = " <<<" if o <= i < o + 16 else ""
        print("  %08X  %-47s  %s%s" % (o, hexs, asc, mark))
    return 0


if __name__ == "__main__":
    sys.exit(main())
