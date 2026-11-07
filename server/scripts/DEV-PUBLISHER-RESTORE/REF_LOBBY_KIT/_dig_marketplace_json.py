# -*- coding: utf-8 -*-
"""深挖 mp/marketplace.json 附近 —— 客户端自己的商城表。

发现: r_48110000_0105A000.bin @0x3FEC26 有 "mp/marketplace.json",
      前面紧邻一串 item ID(10111/10106/10122...)。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_48110000_0105A000.bin")


def main():
    b = open(P, "rb").read()
    i = b.find(b"mp/marketplace.json")
    print("mp/marketplace.json @0x%X" % i)
    print()
    lo = max(0, i - 0x400)
    hi = min(len(b), i + 0x400)
    for o in range(lo, hi, 16):
        chunk = b[o:o + 16]
        hexs = " ".join("%02X" % c for c in chunk)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        mark = " <<<" if o <= i < o + 16 else ""
        print("  %08X  %-47s  %s%s" % (o, hexs, asc, mark))
    print()
    # 找所有 json 资源名
    names = sorted(set(m.group(0).decode("latin1")
                       for m in re.finditer(rb"[a-z0-9_/]*\.json", b)))
    print("文件里引用的 .json 资源名 %d 个:" % len(names))
    for s in names[:40]:
        print("  %s" % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
