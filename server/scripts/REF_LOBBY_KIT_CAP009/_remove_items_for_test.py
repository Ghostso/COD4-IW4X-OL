# -*- coding: utf-8 -*-
"""决定性实验: 从仓库删掉几件, 让用户重买, 看能否加回来。

如果重买后能加回 -> 购买链路正常, 之前"没变化"只是因为**已拥有**。
如果不能加回 -> 链路真的断了。

删哪几件:
    60087 (sku 610, 消耗品 Cat6)
    60088 (sku 611, 消耗品 Cat6)
    22384 (sku 31184, 外观 Cat1)
    17928 (sku 32327, 武器 Cat3)
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(ROOT, "marketplace-inventory.json")
BAK = os.path.join(ROOT, "marketplace-inventory.json.bak_remove_test")
REMOVE = ["60087", "60088", "22384", "17928"]


def main():
    if not os.path.exists(BAK):
        shutil.copy(INV, BAK)
        print("已备份 -> %s" % BAK)
    inv = json.load(open(INV, "r", encoding="utf-8"))
    items = inv.get("Items", {})
    removed = []
    for k in REMOVE:
        if k in items:
            del items[k]
            removed.append(k)
    # Priority 也去掉
    inv["Priority"] = [k for k in inv.get("Priority", []) if k not in REMOVE]
    with open(INV, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, separators=(",", ":"))
    print("已删除: %s" % removed)
    print("剩余 %d 件" % len(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
