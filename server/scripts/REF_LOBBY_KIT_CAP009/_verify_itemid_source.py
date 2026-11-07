# -*- coding: utf-8 -*-
"""验证: 我们目录里的 item 值, 是不是客户端 AS_GetItemIDsFromProduct 会算出的。

方法: exe 目录(marketplace-catalog.json)是**从 exe 反射提取**的,
      它的 Item 字段就是客户端内部表的值 —— 这是权威。
      对同名 SKU, 比较我们(内存提取)与 exe(权威)的 Item。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    exe = {int(e["Id"]): e for e in
           json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                          "r", encoding="utf-8"))}
    cli = {int(e["Id"]): e for e in
           json.load(open(os.path.join(ROOT, "marketplace-catalog-client.json"),
                          "r", encoding="utf-8"))}
    exe_ids = set(exe)
    new = {k: v for k, v in cli.items() if k not in exe_ids}
    print("客户端目录 %d 条, 其中新增 %d 条" % (len(cli), len(new)))
    print()
    # 新增条目的 item 分布
    from collections import Counter
    print("新增条目的 item 范围: %d .. %d"
          % (min(int(v["Item"]) for v in new.values()),
             max(int(v["Item"]) for v in new.values())))
    print("item 值分布 top 10:",
          Counter(int(v["Item"]) for v in new.values()).most_common(10))
    print()
    # 关键: 用户点过的那些, item 是不是"单件唯一"的?
    # 若多个 SKU 共享同一 item, 说明这份数据不可信
    by_item = Counter(int(v["Item"]) for v in new.values())
    dup = [(i, n) for i, n in by_item.items() if n > 1]
    print("新增条目里, 多个 SKU 共用同一 item 的: %d 组" % len(dup))
    for i, n in sorted(dup, key=lambda x: -x[1])[:15]:
        skus = [k for k, v in new.items() if int(v["Item"]) == i]
        print("  item %-6d 被 %d 个 SKU 共用: %s" % (i, n, skus[:8]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
