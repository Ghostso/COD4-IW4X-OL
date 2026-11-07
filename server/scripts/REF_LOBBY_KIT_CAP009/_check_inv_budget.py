# -*- coding: utf-8 -*-
"""核对库存应答体积是否触及客户端上限。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import marketplace_store as ms


def main():
    owner = 16701785630074219790
    inv = json.load(open(os.path.join(ROOT, "marketplace-inventory.json"),
                         "r", encoding="utf-8"))
    items = inv.get("Items", {})
    print("库存件数: %d" % len(items))
    objs = ms.inventory_results(ROOT, owner)
    total = sum(len(o) for o in objs)
    print("inventory_results 返回 %d 个对象, 共 %d 字节" % (len(objs), total))
    print("字节预算 PLAYER_DATA_BUDGET_BYTES = %d" % ms.PLAYER_DATA_BUDGET_BYTES)
    print()
    # 全部条目的总字节
    allbytes = sum(len(ms.inventory_object(owner, int(k), int(v)))
                   for k, v in items.items())
    print("若全部返回: %d 字节 (%.1f KB)" % (allbytes, allbytes / 1024.0))
    print("截断到预算后: %d 字节 (%.1f KB)" % (total, total / 1024.0))
    print("未返回的件数: %d" % (len(items) - len(objs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
