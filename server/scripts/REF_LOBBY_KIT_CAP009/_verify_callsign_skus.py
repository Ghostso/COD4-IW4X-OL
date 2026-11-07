# -*- coding: utf-8 -*-
"""逐个核对"名片类"购买 SKU 的原始内存记录, 确认 +0x14 真的是 item。

SKU: 18079, 31181, 31184, 37251, 39593 (用户实际点过的名片/徽章/称号)
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
STRIDE = 0x60
SKUS = (18079, 31181, 31184, 37251, 39593, 39592)


def main():
    cat = {}
    p = os.path.join(ROOT, "marketplace-catalog.json")
    if os.path.exists(p):
        for e in json.load(open(p, "r", encoding="utf-8")):
            cat.setdefault(int(e["Item"]), []).append(e)

    b = open(MAIN, "rb").read()
    for sku in SKUS:
        print("=" * 78)
        print("SKU %d" % sku)
        pat = struct.pack("<I", sku)
        i = 0
        n = 0
        while n < 3:
            i = b.find(pat, i)
            if i < 0:
                break
            if i + STRIDE <= len(b):
                f = [struct.unpack_from("<I", b, i + k)[0]
                     for k in range(0, STRIDE, 4)]
                if f[1] == 0:
                    print("  @0x%08X  +00=%-7d +04=%-6d +08=%-8d +0C=%-8d "
                          "+10=%-5d +14=%-8d +18=%-10d +1C=%d"
                          % (i, f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7]))
                    n += 1
            i += 4
        if n == 0:
            print("  (无干净记录)")

    print()
    print("=" * 78)
    print("这些 item 在 exe 目录里的 Category:")
    for it in (15166, 22381, 22384, 29892):
        es = cat.get(it)
        if es:
            print("  item %-6d -> %s" % (it, [(e["Id"], e["Category"], e["Currency"]) for e in es]))
        else:
            print("  item %-6d -> 不在 exe 目录" % it)
    return 0


if __name__ == "__main__":
    sys.exit(main())
