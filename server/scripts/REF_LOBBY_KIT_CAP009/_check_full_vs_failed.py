# -*- coding: utf-8 -*-
"""核对: 内存采出来的 full 目录, 是否包含那些"买不到"的 SKU。

若包含 -> 用 full 目录就能修好购买。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FAILED = [37116, 37251, 37253, 16096, 19428, 31184, 31816, 18079,
          39115, 48, 1011, 1981, 15827, 19621, 31173, 31374, 31819, 41314]


def main():
    files = ["marketplace-catalog.json", "marketplace-catalog-full.json",
             "marketplace-catalog-client.json.bak_inferred"]
    ids = {}
    for f in files:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            print("%-50s 缺失" % f)
            continue
        d = {int(e["Id"]): e for e in json.load(open(p, "r", encoding="utf-8"))}
        ids[f] = d
        print("%-50s %6d 条" % (f, len(d)))
    print()
    print("%-8s %-10s %-10s %-10s" % ("sku", "exe", "full(内存)", "inferred"))
    print("-" * 44)
    for s in FAILED:
        row = ["是" if s in ids.get(f, {}) else "否" for f in files]
        print("%-8d %-10s %-10s %-10s" % (s, row[0], row[1], row[2]))
    print()
    # 统计 full 目录的 Category 分布(它的条目怎么填的)
    f = "marketplace-catalog-full.json"
    if f in ids:
        from collections import Counter
        c = Counter(int(e["Category"]) for e in
                    json.load(open(os.path.join(ROOT, f), "r", encoding="utf-8")))
        print("full 目录 Category 分布:", c.most_common())
    return 0


if __name__ == "__main__":
    sys.exit(main())
