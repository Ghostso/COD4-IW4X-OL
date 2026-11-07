# -*- coding: utf-8 -*-
"""用"同时在 exe 目录 + 内存记录"的样本, 建 内存字段 -> Category 的映射。"""
import json
import os
import struct
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
STRIDE = 0x60


def main():
    exe = {int(e["Id"]): e for e in
           json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                          "r", encoding="utf-8"))}
    rec = defaultdict(set)
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for off in range(0, len(b) - STRIDE, 4):
            sku = struct.unpack_from("<I", b, off)[0]
            if sku not in exe:
                continue
            f = [struct.unpack_from("<I", b, off + k)[0]
                 for k in range(0, STRIDE, 4)]
            if f[1] != 0:
                continue
            price = f[3] if 10 <= f[3] <= 10000000 else (
                f[2] if 10 <= f[2] <= 10000000 else 0)
            if price == 0 or price != int(exe[sku]["Price"]):
                continue
            rec[sku].add((f[4], f[6], f[7], f[5]))

    print("价格吻合的 sku: %d" % len(rec))
    print()
    for idx, name in ((1, "+0x18"), (2, "+0x1C")):
        m = defaultdict(Counter)
        for sku, s in rec.items():
            cat = int(exe[sku]["Category"])
            for tup in s:
                m[tup[idx]][cat] += 1
        print("== %s 取值 -> Category ==" % name)
        for v, c in sorted(m.items(), key=lambda x: -sum(x[1].values()))[:15]:
            tot = sum(c.values())
            top = c.most_common(1)[0]
            print("  %-10d 共%-6d 最常见 Cat%d (%d%%)"
                  % (v, tot, top[0], 100 * top[1] // tot))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
