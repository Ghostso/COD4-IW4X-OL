# -*- coding: utf-8 -*-
"""检查运行时物品 ID 是否与库存 key 在同一编号空间。

若运行时 item 大量命中库存 key -> 同一空间, 映射成立。
若命中率接近随机 -> 不同空间。
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    inv = json.load(open(os.path.join(ROOT, "marketplace-inventory.json"),
                         "r", encoding="utf-8"))
    keys = set(int(k) for k in inv.get("Items", {}).keys())
    print("库存 key 数: %d" % len(keys))
    if keys:
        print("库存 key 范围: %d .. %d" % (min(keys), max(keys)))

    rows = list(csv.DictReader(open(
        os.path.join(ROOT, "mkt_assets", "client_catalog.csv"),
        "r", encoding="utf-8-sig")))
    items = [int(r["item"]) for r in rows]
    hit = sum(1 for i in items if i in keys)
    print("运行时记录: %d 条, item 命中库存: %d (%.2f%%)"
          % (len(items), hit, 100.0 * hit / len(items)))
    print("随机基线: %.2f%%" % (100.0 * len(keys) / 500000))

    print()
    print("105 个已点 SKU 的 item 是否在库存里:")
    import re
    clicked = []
    for line in open(os.path.join(ROOT, "unknown_skus.txt"),
                     "r", encoding="utf-8", errors="replace"):
        m = re.match(r"\s*(\d+)", line)
        if m:
            clicked.append(int(m.group(1)))
    clicked = sorted(set(clicked))
    by_sku = {int(r["sku"]): int(r["item"]) for r in rows}
    yes = [s for s in clicked if by_sku.get(s) in keys]
    print("  在库存: %d / %d" % (len(yes), len(clicked)))
    print("  " + ", ".join("%d->%d" % (s, by_sku[s]) for s in yes[:40]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
