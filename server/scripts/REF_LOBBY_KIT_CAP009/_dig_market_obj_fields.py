# -*- coding: utf-8 -*-
"""挖客户端"商品对象/物品对象"的完整字段表。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
SPOTS = (0x4F18078, 0x44E4C58, 0x539BC23)


def main():
    b = open(P, "rb").read()
    for off in SPOTS:
        print("=" * 78)
        print("@0x%X" % off)
        lo = max(0, off - 0x300)
        hi = min(len(b), off + 0x500)
        for s in re.findall(rb"[ -~]{3,80}", b[lo:hi])[:70]:
            print("   %s" % s.decode("latin1"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
