# -*- coding: utf-8 -*-
"""验证 sku -> item 映射是否与客户端一致。

关键: 客户端用 AS_GetItemIDsFromProduct 自己算 itemID。
      如果我们的目录写的 itemID 与它算的不同, 库存里那条就对不上。

验证法: 用**内存里的真实记录**(+0x14 是客户端自己的 itemID)
        与目录里的 Item 对比。
"""
import json
import os
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
STRIDE = 0x60


def main():
    cli = {int(e["Id"]): e for e in
           json.load(open(os.path.join(ROOT, "marketplace-catalog-client.json"),
                          "r", encoding="utf-8"))}
    b = open(MAIN, "rb").read()
    rec = {}
    for off in range(0, len(b) - STRIDE, 4):
        sku = struct.unpack_from("<I", b, off)[0]
        if not (1 <= sku <= 500000):
            continue
        f = [struct.unpack_from("<I", b, off + k)[0]
             for k in range(0, STRIDE, 4)]
        if f[1] != 0 or f[4] > 3650:
            continue
        item = f[5]
        if not (1 <= item <= 500000):
            continue
        rec.setdefault(sku, set()).add(item)

    both = sorted(set(rec) & set(cli))
    print("内存记录 %d 个 SKU, 与客户端目录重叠 %d 个" % (len(rec), len(both)))
    print()
    ok = bad = amb = 0
    badlist = []
    for s in both:
        got = rec[s]
        want = int(cli[s]["Item"])
        if want in got:
            ok += 1
        elif len(got) > 1:
            amb += 1
        else:
            bad += 1
            if len(badlist) < 25:
                badlist.append((s, want, sorted(got)))
    print("目录 item 与内存记录一致: %d" % ok)
    print("内存记录有多个候选(歧义): %d" % amb)
    print("★ 不一致: %d" % bad)
    print()
    for s, want, got in badlist:
        print("  sku=%-7d 目录写 %-7d 内存记录 %s" % (s, want, got))
    return 0


if __name__ == "__main__":
    sys.exit(main())
