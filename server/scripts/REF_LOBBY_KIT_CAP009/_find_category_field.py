# -*- coding: utf-8 -*-
"""在内存记录里找 Category 字段。

已知(用户实测):
    sku=610   -> item=60087  应是 Cat6 (消耗品)
    sku=611   -> item=60088  应是 Cat6
    sku=21718 -> item=60138  应是 Cat6
    sku=32327 -> item=17928  应是 Cat3 (武器)
    sku=31184 -> item=22384  应是 Cat1 (外观)
    sku=19428 -> item=16339  应是 Cat? 

exe 目录里这些 item 的 Category 已知, 用它反查记录里哪个偏移是 Category。
"""
import json
import os
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
STRIDE = 0x60
SKUS = (610, 611, 21718, 32327, 31184, 19428, 1011, 41314, 18079, 37251)


def main():
    cat = json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                         "r", encoding="utf-8"))
    by_item = {}
    for e in cat:
        by_item.setdefault(int(e["Item"]), set()).add(int(e["Category"]))

    b = open(MAIN, "rb").read()
    for sku in SKUS:
        print("=" * 78)
        print("SKU %d" % sku)
        pat = struct.pack("<I", sku)
        i = 0
        n = 0
        while n < 2:
            i = b.find(pat, i)
            if i < 0:
                break
            if i + STRIDE <= len(b):
                f = [struct.unpack_from("<I", b, i + k)[0]
                     for k in range(0, STRIDE, 4)]
                if f[1] == 0 and 1 <= f[5] <= 500000:
                    item = f[5]
                    known = by_item.get(item)
                    print("  @0x%08X item=%-7d exeCat=%s" % (i, item, known))
                    print("     " + " ".join(
                        "+%02X=%-8d" % (k * 4, v) for k, v in enumerate(f[:10])))
                    n += 1
            i += 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
