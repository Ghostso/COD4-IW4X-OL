# -*- coding: utf-8 -*-
"""核对本轮购买的入库结果。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    inv = json.load(open(os.path.join(ROOT, "marketplace-inventory.json"),
                         "r", encoding="utf-8"))
    items = inv.get("Items", {})
    print("库存件数: %d" % len(items))
    print("事务数: %d" % len(inv.get("Transactions", [])))
    print()
    print("本轮相关的 key:")
    for k in ("29892", "29766", "22384", "8270", "16339", "18481", "37251"):
        print("  %-7s -> %s" % (k, items.get(k)))
    acct = json.load(open(os.path.join(ROOT, "player-account.json"),
                          "r", encoding="utf-8"))
    print()
    print("余额: CP=%s GP=%s" % (acct.get("CodPoints"), acct.get("Gold")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
