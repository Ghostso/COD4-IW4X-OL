# -*- coding: utf-8 -*-
"""深挖 cononemarketplaceitems.csv 周边 —— 表内容已是明文。"""
import os
import re
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_48110000_0105A000.bin")
ANCHOR = b"mp/cononemarketplaceitems.csv"


def main():
    b = open(P, "rb").read()
    i = b.find(ANCHOR)
    if i < 0:
        print("没找到")
        return 1
    print("anchor @0x%X" % i)
    lo = max(0, i - 0x2000)
    hi = min(len(b), i + 0x4000)
    seg = b[lo:hi]
    strs = re.findall(rb"[ -~]{6,120}", seg)
    print("可打印串 %d 个:" % len(strs))
    for s in strs[:120]:
        print("   %s" % s.decode("latin1"))
    print()
    for sig in (b"\x78\xda", b"\x78\x9c", b"\x78\x01"):
        start = lo
        n = 0
        while n < 5:
            j = b.find(sig, start, hi)
            if j < 0:
                break
            start = j + 1
            try:
                d = zlib.decompressobj(15)
                out = d.decompress(b[j:j + 8 * 1024 * 1024]) + d.flush()
            except Exception:
                continue
            if out:
                print("zlib @0x%X -> %d 字节, 前 140: %r"
                      % (j, len(out), out[:140]))
                n += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
