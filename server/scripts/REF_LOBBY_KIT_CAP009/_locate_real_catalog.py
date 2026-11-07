# -*- coding: utf-8 -*-
"""用"客户端点过的 SKU + 已知价格"做锚点, 定位真正的商品目录。

锚点(来自 lobby_tasks.bin 的购买请求 + 内存里读到的价格):
    16350 -> 8270
    19428 -> 16339
    31184 -> 22384
    37251 -> 29892
    31816 -> 22486

判据: 在内存里找"同一个区域里**同时**出现多个 (sku, price) 对"的位置 ——
      那才是客户端真正在用的商品表(而不是零散的引用)。
"""
import os
import struct
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")

PAIRS = [(16350, 8270), (19428, 16339), (31184, 22384),
         (37251, 29892), (31816, 22486), (39592, 22384)]


def main():
    pats = [(sku, price, struct.pack("<I", sku), struct.pack("<I", price))
            for sku, price in PAIRS]
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        hits = []
        for sku, price, sp, pp in pats:
            i = b.find(sp)
            if i < 0:
                continue
            # 在该 sku 前后 0x200 内找 price
            lo = max(0, i - 0x200)
            j = b.find(pp, lo, i + 0x200)
            if j >= 0:
                hits.append((sku, price, i, j - i))
        if hits:
            print("%-34s 命中 %d 对: %s"
                  % (fn, len(hits),
                     ", ".join("sku=%d(price@%+d)" % (s, d) for s, _, _, d in hits)))


if __name__ == "__main__":
    main()
