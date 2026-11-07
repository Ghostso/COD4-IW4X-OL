# -*- coding: utf-8 -*-
"""把默认那套名片(原始 7 件)加回仓库。

原始小仓库(2026-10-05 全量赠送之前):
    10007 26666 27724 27725 27720 11016 11722
其中 4 件是 Category=1(外观/名片类):
    27724 27725 27720 11016

用户实测客户端默认装备的就是这一套(背景"抽象-凝烟"/称号"新兵"/徽章"热血战场3")。
全量赠送时被覆盖掉了, 所以军牌定制里没有可换的。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(ROOT, "marketplace-inventory.json")

ORIG7 = ["10007", "26666", "27724", "27725", "27720", "11016", "11722"]


def main():
    inv = json.load(open(INV, "r", encoding="utf-8"))
    items = inv.setdefault("Items", {})
    pri = inv.setdefault("Priority", [])
    added = []
    for k in ORIG7:
        if k not in items:
            items[k] = 1
            added.append(k)
    # 全部置顶, 保证一定发得出去
    for k in reversed(ORIG7):
        if k in pri:
            pri.remove(k)
        pri.insert(0, k)
    seen = set()
    inv["Priority"] = [k for k in pri if not (k in seen or seen.add(k))]
    with open(INV, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, separators=(",", ":"))
    print("新增: %s" % added)
    print("当前仓库: %d 件 -> %s" % (len(items), sorted(items, key=int)))
    print("Priority: %s" % inv["Priority"][:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
