# -*- coding: utf-8 -*-
"""挖 co market items 表名周边 —— 看表是否已解密在附近。"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_48110000_0105A000.bin")
ANCHORS = (b"mp/comarketplaceitems.csv", b"mp/cononemarketplaceitems.csv",
           b"mp/marketplace.json")


def main():
    b = open(P, "rb").read()
    for a in ANCHORS:
        i = b.find(a)
        print("=" * 78)
        if i < 0:
            print("%s: 没找到" % a.decode())
            continue
        print("%s @0x%X" % (a.decode(), i))
        lo = max(0, i - 0x200)
        hi = min(len(b), i + 0x300)
        for s in re.findall(rb"[ -~]{4,90}", b[lo:hi])[:40]:
            print("   %s" % s.decode("latin1"))
        print("   附近 u32 (1000..999999):")
        shown = 0
        o = lo
        while o < hi - 3 and shown <= 20:
            v = struct.unpack_from("<I", b, o)[0]
            if 1000 <= v <= 999999:
                print("     @0x%X = %d" % (o, v))
                shown += 1
            o += 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
