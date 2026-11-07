# -*- coding: utf-8 -*-
"""检查补充 SKU 的货币设定。39593 客户端是走 93/131(GP) 买的。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    cat = json.load(open(os.path.join(ROOT, "marketplace-catalog-client.json"),
                         "r", encoding="utf-8"))
    by_id = {int(e["Id"]): e for e in cat}
    print("总条目: %d" % len(cat))
    print()
    for s in (31181, 31184, 37251, 39592, 39593, 16350, 19428):
        e = by_id.get(s)
        if not e:
            print("  sku=%-7d 不在目录里" % s)
            continue
        cur = "CP" if e["Currency"] == 1 else "GP"
        print("  sku=%-7d item=%-7d price=%-7d %s days=%d"
              % (s, e["Item"], e["Price"], cur, e["SelectedDays"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
