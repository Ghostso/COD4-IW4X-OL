# -*- coding: utf-8 -*-
"""在内存里直接找 CSV/表字段名的明文特征。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
KEYS = [b"skuId", b"itemId", b"productId", b"sku_id", b"item_id",
        b"product_id", b"coMarketplace", b"unlockFlags",
        b"categoryId", b"itemType", b"coMarketplaceProductItems"]


def main():
    for key in KEYS:
        hits = []
        for fn in sorted(os.listdir(MEM)):
            p = os.path.join(MEM, fn)
            if not os.path.isfile(p):
                continue
            try:
                b = open(p, "rb").read()
            except Exception:
                continue
            i = b.find(key)
            if i >= 0:
                hits.append((fn, i))
                if len(hits) >= 6:
                    break
        print("== %-28s %d 处" % (key.decode(), len(hits)))
        for fn, i in hits[:3]:
            b = open(os.path.join(MEM, fn), "rb").read()
            lo = max(0, i - 80)
            hi = min(len(b), i + 120)
            txt = "".join(chr(c) if 32 <= c < 127 else "." for c in b[lo:hi])
            print("   %s @0x%X" % (fn, i))
            print("      %s" % txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
