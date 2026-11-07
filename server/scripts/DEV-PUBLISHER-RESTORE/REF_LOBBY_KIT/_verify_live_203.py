# -*- coding: utf-8 -*-
"""验证当前库存的 203 应答内容: 优先级物品是否在最前面。"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import marketplace_store as ms

OWNER = 16701785630074219790


def item_of(o):
    return struct.unpack_from("<I", o, 15)[0]


def main():
    inv = json.load(open(os.path.join(ROOT, "marketplace-inventory.json"),
                         "r", encoding="utf-8"))
    print("库存件数: %d" % len(inv.get("Items", {})))
    print("Priority: %s" % inv.get("Priority"))
    print("目录: %s" % os.path.basename(ms.catalog_path()))
    print("预算: %d" % ms.inventory_budget())
    print()

    objs = ms.inventory_results(ROOT, OWNER)
    print("203 应答: %d 件, %d 字节" % (len(objs), sum(len(o) for o in objs)))
    print("前 12 件的 item: %s" % [item_of(o) for o in objs[:12]])
    sent = set(item_of(o) for o in objs)
    print()
    print("关键物品是否在应答里:")
    for k in (29892, 22381, 22384, 18481, 8270, 16339):
        in_inv = str(k) in inv.get("Items", {})
        print("  item %-6d 库存里=%-5s 应答里=%s"
              % (k, in_inv, k in sent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
