# -*- coding: utf-8 -*-
"""检查主仓库里混进了多少"名片类"道具。

判断依据: exe 目录里 item -> Category。Category=1 是外观类(名片/徽章等),
Category=3 是武器类。也对比原始 7 件小仓库。
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(ROOT, "marketplace-catalog.json")
INV = os.path.join(ROOT, "marketplace-inventory.json")
OLD = os.path.join(ROOT, "marketplace-inventory.json.bak_before_allitems_20261005_171532")


def main():
    cat = json.load(open(CAT, "r", encoding="utf-8"))
    item_cat = {}
    for e in cat:
        item_cat.setdefault(int(e["Item"]), set()).add(int(e["Category"]))

    inv = json.load(open(INV, "r", encoding="utf-8"))
    items = [int(k) for k in inv.get("Items", {})]
    print("当前仓库: %d 件" % len(items))

    known = [i for i in items if i in item_cat]
    print("其中 exe 目录认识: %d (%.1f%%)"
          % (len(known), 100.0 * len(known) / len(items)))
    print()

    c = Counter()
    for i in items:
        cats = item_cat.get(i)
        if cats is None:
            c["未知(不在 exe 目录)"] += 1
        else:
            for x in cats:
                c["Category=%d" % x] += 1
    print("按 exe Category 统计:")
    for k, v in c.most_common():
        print("  %-24s %d" % (k, v))
    print()

    cat1 = [i for i in items if item_cat.get(i) and 1 in item_cat[i]]
    print("Category=1(外观类) 共 %d 件, 前 30:" % len(cat1))
    print("  %s" % cat1[:30])
    print()

    if os.path.exists(OLD):
        old = json.load(open(OLD, "r", encoding="utf-8"))
        oi = [int(k) for k in old.get("Items", {})]
        print("原始仓库: %d 件 -> %s" % (len(oi), oi))
        for i in oi:
            print("  item %-6d -> exe Category %s" % (i, item_cat.get(i)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
