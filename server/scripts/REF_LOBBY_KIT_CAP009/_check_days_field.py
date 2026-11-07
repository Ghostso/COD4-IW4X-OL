# -*- coding: utf-8 -*-
"""核对 +0x10 是否等于 exe 目录的 SelectedDays(时长天数)。"""
import json
import os
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
CAT = os.path.join(ROOT, "marketplace-catalog.json")
NONE = 0xFFFFFFFF
STRIDE = 0x60


def main():
    cat = {int(e["Id"]): e for e in json.load(open(CAT, "r", encoding="utf-8"))}
    b = open(MAIN, "rb").read()
    recs = {}
    for off in range(0, len(b) - STRIDE, 4):
        sku = struct.unpack_from("<I", b, off)[0]
        if sku not in cat:
            continue
        f = [struct.unpack_from("<I", b, off + k)[0] for k in range(0, STRIDE, 4)]
        if f[1] != 0:
            continue
        if f[7] != NONE and not (0 <= f[7] <= 15):
            continue
        price = f[3] if 10 <= f[3] <= 10000000 else 0
        if price == 0 and 10 <= f[2] <= 10000000:
            price = f[2]
        if price == 0:
            continue
        if price != int(cat[sku]["Price"]):
            continue
        recs.setdefault(sku, f)

    print("价格吻合的记录: %d 条" % len(recs))
    eq = 0
    dist = Counter()
    for s, f in recs.items():
        want = int(cat[s].get("SelectedDays", 0))
        got = f[4]
        dist[(want, got)] += 1
        if want == got:
            eq += 1
    print("  +0x10 == exe.SelectedDays : %d / %d" % (eq, len(recs)))
    print()
    print("(exe.SelectedDays, +0x10) 分布 top 15:")
    for (w, g), n in dist.most_common(15):
        print("  exe=%-6d mem=%-6d x%d" % (w, g, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
