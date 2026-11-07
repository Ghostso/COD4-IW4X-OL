# -*- coding: utf-8 -*-
"""验证: 库存按 item ID 升序截断, 高 ID 的物品被截掉了 -> 客户端看不见。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import marketplace_store as ms


def main():
    inv = json.load(open(os.path.join(ROOT, "marketplace-inventory.json"),
                         "r", encoding="utf-8"))
    keys = sorted((int(k) for k in inv["Items"]), key=lambda k: k)
    present = set(keys)
    print("库存总件数: %d" % len(keys))
    print("最小 item: %d, 最大 item: %d" % (keys[0], keys[-1]))
    print()

    owner = 16701785630074219790
    objs = ms.inventory_results(ROOT, owner)
    print("默认预算下发出去: %d 件" % len(objs))
    sent = set(keys[:len(objs)])
    print("发出去的最大 item: %d" % max(sent))
    print()
    print("关键物品:")
    for k in (22381, 22384, 29892, 8270, 16339, 18481, 13, 51):
        if k not in present:
            state = "库存里没有"
        elif k in sent:
            state = "已发出"
        else:
            state = "★在库存里但被截掉★"
        print("  item %-6d -> %s" % (k, state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
