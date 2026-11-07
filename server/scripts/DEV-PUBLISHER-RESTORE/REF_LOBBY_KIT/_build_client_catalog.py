# -*- coding: utf-8 -*-
"""把运行时提取的客户端 SKU 合进一份**独立**目录文件。

不动现有的 marketplace-catalog.json（那是唯一能让大厅稳定运行的版本）。
输出 marketplace-catalog-client.json，客户端 SKU 覆盖同名 exe 条目。

字段映射:
  Id           <- sku
  Item         <- 运行时 +0x14
  Price        <- 运行时 +0x08/+0x0C
  Category     <- 运行时 +0x1C(0..7; 其余归 0)
  Currency     <- 来自实际购买帧走的服务号(80->1 CP, 93->2 GP)
  Stackable    <- False
  Grant        <- 1
  SelectedDays <- 运行时 +0x10(时长天数; 0=永久)
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_CAT = os.path.join(ROOT, "marketplace-catalog.json")
SRC_CSV = os.path.join(ROOT, "mkt_assets", "client_catalog.csv")
EXTRA_CSV = os.path.join(ROOT, "mkt_assets", "extra_skus.csv")
CUR_CSV = os.path.join(ROOT, "mkt_assets", "sku_currency.csv")
OUT = os.path.join(ROOT, "marketplace-catalog-client.json")


def main():
    base = json.load(open(SRC_CAT, "r", encoding="utf-8"))
    by_id = {}
    for e in base:
        by_id[int(e["Id"])] = dict(e)

    rows = list(csv.DictReader(open(SRC_CSV, "r", encoding="utf-8-sig")))
    # 追加"客户端点过但主提取没覆盖到"的 SKU(如 39593)
    if os.path.exists(EXTRA_CSV):
        extra = list(csv.DictReader(open(EXTRA_CSV, "r", encoding="utf-8-sig")))
        have = set(int(r["sku"]) for r in rows)
        add = [r for r in extra if int(r["sku"]) not in have]
        rows.extend(add)
        print("额外补入 %d 条 (来自 extra_skus.csv)" % len(add))
    cur = {}
    if os.path.exists(CUR_CSV):
        for r in csv.DictReader(open(CUR_CSV, "r", encoding="utf-8-sig")):
            cur[int(r["sku"])] = int(r["currency"])
    added = 0
    updated = 0
    no_cur = 0
    for r in rows:
        sku = int(r["sku"])
        item = int(r["item"])
        price = int(r["price"])
        if not (1 <= sku <= 500000 and 1 <= item <= 500000):
            continue
        if not (1 <= price <= 10000000):
            continue
        if sku not in cur:
            no_cur += 1
        days = int(r.get("days", 0) or 0)
        if not (0 <= days <= 3650):
            days = 0
        entry = {
            "Id": sku,
            "Item": item,
            "Currency": cur.get(sku, 1),
            "Price": price,
            "Category": 0,
            "Stackable": False,
            "Grant": 1,
            "SelectedDays": days,
        }
        if sku in by_id:
            updated += 1
        else:
            added += 1
        by_id[sku] = entry

    out = [by_id[k] for k in sorted(by_id)]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("基础目录 %d 条, 新增 %d, 覆盖 %d -> 合计 %d"
          % (len(base), added, updated, len(out)))
    print("其中无购买帧货币记录的: %d (按 CP 处理)" % no_cur)
    print("输出: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
