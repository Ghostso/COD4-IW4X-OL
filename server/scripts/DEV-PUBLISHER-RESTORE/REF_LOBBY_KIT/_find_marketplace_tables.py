# -*- coding: utf-8 -*-
"""在明文 common_marketplace 资源包里找商品/物品映射表。

背景: exe 目录与客户端购买帧的 SKU 是两套编号; 用户点过的 105 个 SKU
      只在运行时出现。物品 ID 需要从游戏资源里找。

做法: 遍历已抽出的资源路径清单, 找表类文件
      (.csv/.txt/.json/.cfg/table 等), 再按关键词过滤。
"""
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(ROOT, "mkt_assets", "mkt_assets_table.csv")

KEY = re.compile(r"(marketplace|market|store|shop|sku|product|item|"
                 r"callsign|badge|emblem|title|nameplate|playlist|"
                 r"bundle|offer|price|currency|purchase)", re.I)
EXT = (".csv", ".txt", ".json", ".cfg", ".table", ".dat", ".info")


def main():
    rows = list(csv.DictReader(open(TABLE, "r", encoding="utf-8-sig")))
    print("资源表条目: %d" % len(rows))

    tables = {}
    for r in rows:
        p = (r.get("path") or "").replace("\\", "/")
        low = p.lower()
        if low.endswith(EXT):
            tables.setdefault(p, 0)
            tables[p] += 1

    print("疑似表文件: %d" % len(tables))
    print()
    print("== 命中关键词的表文件 ==")
    n = 0
    for p in sorted(tables):
        if KEY.search(p):
            n += 1
            if n <= 200:
                print("  %s" % p)
    print("共 %d 个" % n)

    print()
    print("== 所有 .csv / .json / .cfg 文件 ==")
    n2 = 0
    for p in sorted(tables):
        if p.lower().endswith((".csv", ".json", ".cfg")):
            n2 += 1
            if n2 <= 200:
                print("  %s" % p)
    print("共 %d 个" % n2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
