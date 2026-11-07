# -*- coding: utf-8 -*-
"""把"客户端点过但目录里没有"的 SKU, 用内存记录补出来。

已确认的规则:
  - 记录 0x60 步长, +0x00=SKU, +0x08/+0x0C=价格, +0x10=天数, +0x14=item, +0x1C=类型
  - 同一 SKU 若出现多个不同 item -> 丢弃(噪声)

用途: 39593 这种客户端点过、但之前没采到的 SKU, 直接从内存里补。
"""
import csv
import json
import os
import struct
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
MAIN = os.path.join(MEMDIR, "r_259D0000_06400000.bin")
OUT = os.path.join(ROOT, "mkt_assets", "extra_skus.csv")
NONE = 0xFFFFFFFF
STRIDE = 0x60


def main():
    targets = [int(a) for a in sys.argv[1:]]
    if not targets:
        # 默认补这几个: 39593 及其邻居, 以及常见连续段
        targets = list(range(39588, 39600)) + [31181, 31184]
    wanted = set(targets)
    print("目标 SKU: %s" % sorted(wanted))

    b = open(MAIN, "rb").read()
    acc = defaultdict(Counter)
    for off in range(0, len(b) - STRIDE, 4):
        sku = struct.unpack_from("<I", b, off)[0]
        if sku not in wanted:
            continue
        f04 = struct.unpack_from("<I", b, off + 4)[0]
        f08 = struct.unpack_from("<I", b, off + 8)[0]
        f0c = struct.unpack_from("<I", b, off + 0xC)[0]
        f10 = struct.unpack_from("<I", b, off + 0x10)[0]
        item = struct.unpack_from("<I", b, off + 0x14)[0]
        f1c = struct.unpack_from("<I", b, off + 0x1C)[0]
        if f04 != 0:
            continue
        if f1c != NONE and not (0 <= f1c <= 15):
            continue
        if f10 > 3650:
            continue
        if not (1 <= item <= 500000):
            continue
        price = f0c if 10 <= f0c <= 10000000 else 0
        if price == 0 and 10 <= f08 <= 10000000:
            price = f08
        if price == 0:
            continue
        acc[sku][(price, item, f10)] += 1

    rows = []
    for sku in sorted(acc):
        items = set(k[1] for k in acc[sku])
        if len(items) > 1:
            print("  sku=%-7d 物品 ID 冲突, 丢弃: %s"
                  % (sku, acc[sku].most_common(4)))
            continue
        (price, item, days), votes = acc[sku].most_common(1)[0]
        rows.append({"sku": sku, "price": price, "item": item,
                     "days": days, "votes": votes})
        print("  sku=%-7d price=%-8d item=%-8d days=%-4d (v=%d)"
              % (sku, price, item, days, votes))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "price", "item", "days", "votes"])
        w.writeheader()
        w.writerows(rows)
    print("导出 %d 条 -> %s" % (len(rows), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
