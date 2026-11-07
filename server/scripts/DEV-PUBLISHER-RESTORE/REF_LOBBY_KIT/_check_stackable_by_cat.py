# -*- coding: utf-8 -*-
"""看 exe 目录里各 Category 的 Stackable / Grant / SelectedDays 分布。

如果 Category=6(消耗品/加成卡) 在 exe 里是 Stackable=True,
而我们新增的条目全写 False, 那就是我们抄错了。
"""
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    exe = json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                         "r", encoding="utf-8"))
    cli = json.load(open(os.path.join(ROOT, "marketplace-catalog-client.json"),
                         "r", encoding="utf-8"))

    def stat(cat, label):
        bycat = defaultdict(Counter)
        for e in cat:
            c = int(e["Category"])
            bycat[c]["总"] += 1
            if e.get("Stackable"):
                bycat[c]["可堆叠"] += 1
            bycat[c]["Grant=%s" % e.get("Grant")] += 1
            bycat[c]["Days=%s" % e.get("SelectedDays")] += 1
        print("== %s ==" % label)
        for c in sorted(bycat):
            d = bycat[c]
            print("  Cat%-2d 总%-6d 可堆叠%-6d Grant分布=%s"
                  % (c, d["总"], d["可堆叠"],
                     {k: v for k, v in d.items() if k.startswith("Grant")}))
        print()

    stat(exe, "exe 目录")
    stat(cli, "客户端目录")

    # 客户端目录里新增的那批(不在 exe 里)
    exe_ids = set(int(e["Id"]) for e in exe)
    new = [e for e in cli if int(e["Id"]) not in exe_ids]
    print("客户端目录新增 %d 条:" % len(new))
    print("  Category 分布:", Counter(int(e["Category"]) for e in new).most_common())
    print("  Stackable 分布:", Counter(bool(e.get("Stackable")) for e in new).most_common())
    return 0


if __name__ == "__main__":
    sys.exit(main())
