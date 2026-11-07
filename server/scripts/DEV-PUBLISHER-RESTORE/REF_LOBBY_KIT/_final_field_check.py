# -*- coding: utf-8 -*-
"""最终字段判定。

候选记录(0x60 步长, 来自 r_259D0000_06400000.bin):
  +0x00 SKU
  +0x08 价格(变体 A)
  +0x0C 价格(变体 B)
  +0x14 待定
  +0x1C 类别

判定标准:
  * 价格: 与 exe 目录 Price 的重合率
  * +0x14: 与 exe 目录 Item 集合的重合率, 对比随机基线
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
CAT = os.path.join(ROOT, "marketplace-catalog.json")
INV = os.path.join(ROOT, "marketplace-inventory.json")
STRIDE = 0x60


def main():
    cat = json.load(open(CAT, "r", encoding="utf-8"))
    by_id = {int(e["Id"]): e for e in cat}
    item_set = set(int(e["Item"]) for e in cat)
    inv = json.load(open(INV, "r", encoding="utf-8"))
    inv_keys = set(int(k) for k in inv.get("Items", {}).keys())

    print("exe 目录: %d 条, 物品 ID 去重 %d 个" % (len(cat), len(item_set)))
    print("库存: %d 件" % len(inv_keys))

    # 收集候选
    recs = {}
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
            if not (1 <= sku <= 500000):
                continue
            f = [struct.unpack_from("<I", b, off + k)[0] for k in range(0, STRIDE, 4)]
            if f[1] != 0 or f[4] != 0:
                continue
            price = f[3] if f[3] else f[2]
            if not (1 <= price <= 10000000):
                continue
            if not (1 <= f[5] <= 500000):
                continue
            recs.setdefault(sku, []).append((price, f[5], f[7]))

    print("候选记录 SKU: %d" % len(recs))

    both = sorted(set(recs) & set(by_id))
    print("与 exe 目录重叠: %d" % len(both))

    hit_price = sum(1 for s in both
                    if any(p == int(by_id[s]["Price"]) for p, _, _ in recs[s]))
    hit_item = sum(1 for s in both
                   if any(i == int(by_id[s]["Item"]) for _, i, _ in recs[s]))
    print("  +0x0C/+0x08 == exe.Price : %d / %d" % (hit_price, len(both)))
    print("  +0x14       == exe.Item  : %d / %d" % (hit_item, len(both)))

    # +0x14 落在 exe.Item 全集 / 库存的比例(对比随机基线)
    all14 = [i for s in recs for _, i, _ in recs[s]]
    in_itemset = sum(1 for i in all14 if i in item_set)
    in_inv = sum(1 for i in all14 if i in inv_keys)
    print()
    print("全部候选 %d 条:" % len(all14))
    print("  +0x14 落在 exe.Item 全集: %d (%.1f%%)"
          % (in_itemset, 100.0 * in_itemset / len(all14)))
    print("  +0x14 落在库存:            %d (%.1f%%)"
          % (in_inv, 100.0 * in_inv / len(all14)))
    print("  随机基线(1..500000): %.1f%%"
          % (100.0 * len(item_set) / 500000))

    print()
    print("105 个已点 SKU 的最终取值:")
    import re
    clicked = []
    for line in open(os.path.join(ROOT, "unknown_skus.txt"),
                     "r", encoding="utf-8", errors="replace"):
        m = re.match(r"\s*(\d+)", line)
        if m:
            clicked.append(int(m.group(1)))
    clicked = sorted(set(clicked))
    print("%-8s %-10s %-10s %-10s" % ("sku", "price", "item", "category"))
    for s in clicked:
        if s not in recs:
            print("%-8d %-10s %-10s %-10s" % (s, "-", "-", "-"))
            continue
        p, i, c = recs[s][0]
        print("%-8d %-10d %-10d %-10s" % (s, p, i, c if c != 0xFFFFFFFF else "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
