# -*- coding: utf-8 -*-
"""核对 sku=18079 这次购买: 库存有没有、203 有没有发出去、item 是否=sku。"""
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
    items = inv.get("Items", {})
    print("库存件数: %d" % len(items))
    print("Items: %s" % items)
    print("Priority: %s" % inv.get("Priority"))
    print()
    objs = ms.inventory_results(ROOT, OWNER)
    print("203 应答 %d 件:" % len(objs))
    for o in objs:
        print("  item=%d" % item_of(o))
    print()
    # 目录里 18079 是什么
    for name in ("marketplace-catalog-client.json", "marketplace-catalog.json"):
        p = os.path.join(ROOT, name)
        cat = json.load(open(p, "r", encoding="utf-8"))
        e = next((x for x in cat if int(x["Id"]) == 18079), None)
        print("%s 里 18079 -> %s" % (name, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
