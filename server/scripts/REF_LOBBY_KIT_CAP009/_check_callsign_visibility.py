# -*- coding: utf-8 -*-
"""检查名片类道具(Category=1)有多少落在 480KB 截断线之内。

客户端 80/203 请求要 20000 件, 我们只能发 ~7741 件。
这里统计: 按 item ID 升序排, 前 7741 件里有多少 Category=1。
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(ROOT, "marketplace-catalog.json")
INV = os.path.join(ROOT, "marketplace-inventory.json")


def main():
    cat = json.load(open(CAT, "r", encoding="utf-8"))
    item_cat = {}
    for e in cat:
        item_cat.setdefault(int(e["Item"]), set()).add(int(e["Category"]))

    inv = json.load(open(INV, "r", encoding="utf-8"))
    keys = sorted((int(k) for k in inv.get("Items", {})))
    print("仓库 %d 件" % len(keys))

    # 模拟"按 ID 升序发 7741 件"
    sent = keys[:7741]
    cut = keys[7741 - 1]
    print("按 ID 升序发 %d 件, 最大 item = %d" % (len(sent), cut))
    print()

    def stat(lst, label):
        c = Counter()
        for i in lst:
            cats = item_cat.get(i)
            if cats is None:
                c["未知"] += 1
            else:
                for x in cats:
                    c["Cat%d" % x] += 1
        print("%s: %s" % (label, dict(c.most_common())))

    stat(keys, "全仓库")
    stat(sent, "★ 实际发出去的前 7741 件")
    stat(keys[7741:], "★ 被截掉没发的")
    print()

    # 用户买过的三件
    print("用户买过的:")
    for i in (29892, 22381, 22384):
        pos = keys.index(i) if i in keys else -1
        print("  item %-6d 排名 %-6d %s"
              % (i, pos + 1,
                 "在发送范围" if 0 <= pos < 7741 else "★被截掉★"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
