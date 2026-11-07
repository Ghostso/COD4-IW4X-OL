# -*- coding: utf-8 -*-
"""深挖 IsMarketplaceItemOwned / isOwned 附近的完整数据流。

目标: 弄清客户端判断"已拥有"时读的是哪个数据结构 ——
      是 marketplace inventory(203), 还是别的表。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")


def dump_around(b, off, span=0x300, label=""):
    lo = max(0, off - span)
    hi = min(len(b), off + span)
    strs = re.findall(rb"[ -~]{3,100}", b[lo:hi])
    print("  %s @0x%X (%d 个串):" % (label, off, len(strs)))
    for s in strs[:50]:
        print("      %s" % s.decode("latin1"))


def main():
    b = open(P, "rb").read()
    for key in (b"IsMarketplaceItemOwned", b"isOwned",
                b"AS_GetItemIDsFromProduct", b"MKT_RequestAccountInfo",
                b"MKT_InvalidatePreviewList", b"WL_FillInInventoryProductItems"):
        i = b.find(key)
        print("=" * 76)
        if i < 0:
            print("%s: 没找到" % key.decode())
            continue
        dump_around(b, i, 0x260, key.decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
