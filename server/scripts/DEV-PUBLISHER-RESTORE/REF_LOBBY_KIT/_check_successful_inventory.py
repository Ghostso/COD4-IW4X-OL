# -*- coding: utf-8 -*-
"""核实: 那几笔"买成功"的, 到底有没有真的进库存?

区分: 已在库存(全量赠送过) vs 新入库
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# 本轮买过的 SKU -> item
BUYS = [(610, 60087), (611, 60088), (21718, 60138), (32327, 17928),
        (19428, 16339), (31184, 22384), (37251, 29892), (18079, 15166)]


def main():
    inv = json.load(open(os.path.join(ROOT, "marketplace-inventory.json"),
                         "r", encoding="utf-8"))
    items = inv.get("Items", {})
    print("库存 %d 件, 事务 %d 条"
          % (len(items), len(inv.get("Transactions", []))))
    print()
    print("%-8s %-8s %-10s %s" % ("sku", "item", "在库存", "备注"))
    for sku, item in BUYS:
        have = str(item) in items
        print("%-8d %-8d %-10s %s"
              % (sku, item, "是" if have else "★否",
                 "已拥有, 不重复加" if have else "★未入库"))
    print()
    print("Priority: %s" % inv.get("Priority", [])[:12])
    #
    # 备份文件里的原始 7 件
    bak = os.path.join(ROOT, "marketplace-inventory.json.bak_big")
    if os.path.exists(bak):
        b = json.load(open(bak, "r", encoding="utf-8"))
        print()
        print("bak_big: %d 件" % len(b.get("Items", {})))
        for k in ("60087", "60088", "60138", "17928", "16339", "22384"):
            print("  item %-6s 在 bak: %s" % (k, k in b.get("Items", {})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
