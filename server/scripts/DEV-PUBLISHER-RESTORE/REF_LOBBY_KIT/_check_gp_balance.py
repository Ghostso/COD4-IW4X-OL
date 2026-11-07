# -*- coding: utf-8 -*-
"""核对购买后的 GP/CP 余额是否与扣款一致。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    a = json.load(open(os.path.join(ROOT, "player-account.json"),
                       "r", encoding="utf-8"))
    inv = json.load(open(os.path.join(ROOT, "marketplace-inventory.json"),
                         "r", encoding="utf-8"))
    print("CP = %s" % a.get("CodPoints"))
    print("GP = %s" % a.get("Gold"))
    print("库存件数 = %d" % len(inv.get("Items", {})))
    print("事务数 = %d" % len(inv.get("Transactions", [])))
    print()
    print("三件商品当前库存值:")
    items = inv.get("Items", {})
    for k in ("22381", "22384", "29892"):
        print("  %-6s -> %s" % (k, items.get(k)))
    print()
    print("预期: CP 973799 (981799-8000), GP 818639 (819999-680-680)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
