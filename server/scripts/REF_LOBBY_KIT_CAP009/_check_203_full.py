# -*- coding: utf-8 -*-
"""核对 203 应答: 体积、件数、关键 item 是否在内。"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import marketplace_store as ms

OWNER = 16701785630074219790
KEY = [60087, 60088, 60138, 17928, 16339, 22384, 29892, 15166, 18481, 22381]


def item_of(o):
    return struct.unpack_from("<I", o, 15)[0]


def main():
    inv = json.load(open(os.path.join(ROOT, "marketplace-inventory.json"),
                         "r", encoding="utf-8"))
    print("库存 %d 件" % len(inv.get("Items", {})))
    objs = ms.inventory_results(ROOT, OWNER)
    total = sum(len(o) for o in objs)
    print("203 应答 %d 件, %d 字节 (%.0f KB), 预算 %d"
          % (len(objs), total, total / 1024.0, ms.inventory_budget()))
    print("未发出: %d 件" % (len(inv.get("Items", {})) - len(objs)))
    print()
    sent = set(item_of(o) for o in objs)
    print("关键 item 是否发出:")
    for k in KEY:
        print("  %-6d %s" % (k, "★发出" if k in sent else "未发出"))
    print()
    print("应答前 12 件: %s" % [item_of(o) for o in objs[:12]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
