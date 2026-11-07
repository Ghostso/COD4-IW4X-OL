# -*- coding: utf-8 -*-
"""查默认名片那套的 item ID(原始 7 件仓库里的 Category=1 项)。

用户实测默认: 背景"抽象-凝烟" 称号"新兵" 徽章"热血战场3"
原始 7 件: 10007 26666 27724 27725 27720 11016 11722
其中 Category=1(外观类): 27724 27725 27720 11016
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ORIG7 = [10007, 26666, 27724, 27725, 27720, 11016, 11722]
NEW = [15166, 22381, 22384, 29892]


def main():
    cat = json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                         "r", encoding="utf-8"))
    by_item = {}
    for e in cat:
        by_item.setdefault(int(e["Item"]), []).append(e)

    print("== 原始 7 件小仓库 ==")
    for it in ORIG7:
        es = by_item.get(it, [])
        print("  item %-6d -> %s"
              % (it, [(e["Id"], "Cat%d" % e["Category"],
                       "CP" if e["Currency"] == 1 else "GP") for e in es]))
    print()
    print("== 我们买到的 4 件 ==")
    for it in NEW:
        es = by_item.get(it, [])
        print("  item %-6d -> %s"
              % (it, [(e["Id"], "Cat%d" % e["Category"],
                       "CP" if e["Currency"] == 1 else "GP") for e in es]))
    print()
    # 这些 item 是否在当前仓库里
    inv = json.load(open(os.path.join(ROOT, "marketplace-inventory.json"),
                         "r", encoding="utf-8"))
    have = set(int(k) for k in inv.get("Items", {}))
    print("当前仓库 %d 件" % len(have))
    for it in ORIG7:
        print("  原始 item %-6d 在仓库: %s" % (it, it in have))
    print()
    for it in NEW:
        print("  新买 item %-6d 在仓库: %s" % (it, it in have))
    return 0


if __name__ == "__main__":
    sys.exit(main())
