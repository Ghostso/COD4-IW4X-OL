# -*- coding: utf-8 -*-
"""把已买过的物品排到库存应答最前面, 让客户端能看见。

用途: 之前因为 480KB 截断, 高 ID 物品(22381/22384/29892/18481...)没发出去,
      游戏内表现是"买到了但仓库里不出现"。这里把用户实际买过的物品置顶。

注意: 只动 Priority 数组, 不改 Items 数量。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(ROOT, "marketplace-inventory.json")

SEED = ["22384", "22381", "29892", "18481"]


def main():
    inv = json.load(open(INV, "r", encoding="utf-8"))
    items = inv.setdefault("Items", {})
    pri = inv.setdefault("Priority", [])
    added = []
    for k in SEED:
        if k in items:
            if k in pri:
                pri.remove(k)
            pri.insert(0, k)
            added.append(k)
    seen = set()
    inv["Priority"] = [k for k in pri if not (k in seen or seen.add(k))]
    with open(INV, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, separators=(",", ":"))
    print("已置顶: %s" % added)
    print("Priority = %s" % inv["Priority"][:20])
    print("库存件数 = %d" % len(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
