# -*- coding: utf-8 -*-
"""把**内存里所有能采到的真实 SKU** 灌进目录 —— 不再只补"点过的"。

根因: 商城有大量 SKU, 只补用户点过的 101 条 -> 每点一个新商品都
      "Unsupported SKU/currency/quantity" 失败。

数据源: mem_linear 全部转储, 用已验证的 0x60 布局:
    +0x00 SKU  +0x08/+0x0C 价格  +0x10 时长  +0x14 item  +0x1C 类型

判据(每条都过审计):
    +0x04 == 0
    +0x1C 是 -1 或 0..15
    +0x10 <= 3650
    item 在 1..500000
    价格 >= 10
    同一 SKU 若出现多个不同 item -> 丢弃

货币: 优先用 sku_currency.csv(真实购买帧), 其次按 exe 目录同名 SKU, 默认 CP。
输出: marketplace-catalog-full.json  (另存, 不动现有目录)
"""
import csv
import json
import os
import struct
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
OUT = os.path.join(ROOT, "marketplace-catalog-full.json")
NONE = 0xFFFFFFFF
STRIDE = 0x60


def collect():
    acc = defaultdict(Counter)
    files = 0
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        files += 1
        for off in range(0, len(b) - STRIDE, 4):
            sku = struct.unpack_from("<I", b, off)[0]
            if not (1 <= sku <= 500000):
                continue
            f04 = struct.unpack_from("<I", b, off + 4)[0]
            f08 = struct.unpack_from("<I", b, off + 8)[0]
            f0c = struct.unpack_from("<I", b, off + 0xC)[0]
            f10 = struct.unpack_from("<I", b, off + 0x10)[0]
            item = struct.unpack_from("<I", b, off + 0x14)[0]
            f1c = struct.unpack_from("<I", b, off + 0x1C)[0]
            if f04 != 0:
                continue
            if f1c != NONE and not (0 <= f1c <= 15):
                continue
            if f10 > 3650:
                continue
            if not (1 <= item <= 500000):
                continue
            price = f0c if 10 <= f0c <= 10000000 else 0
            if price == 0 and 10 <= f08 <= 10000000:
                price = f08
            if price == 0:
                continue
            acc[sku][(price, item, f10)] += 1
    return acc, files


def main():
    acc, files = collect()
    print("扫 %d 个区, 候选 SKU %d 个" % (files, len(acc)))

    rows = []
    dropped = []
    for sku in sorted(acc):
        items = set(k[1] for k in acc[sku])
        if len(items) > 1:
            dropped.append(sku)
            continue
        (price, item, days), votes = acc[sku].most_common(1)[0]
        rows.append((sku, item, price, days, votes))
    print("可用 SKU %d 个, 因 item 冲突丢弃 %d 个" % (len(rows), len(dropped)))
    if dropped:
        print("  丢弃样例: %s" % dropped[:20])

    # 货币
    cur = {}
    p = os.path.join(ROOT, "mkt_assets", "sku_currency.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p, "r", encoding="utf-8-sig")):
            cur[int(r["sku"])] = int(r["currency"])

    # 基础目录(拿 exe 的 Currency/Category/Stackable 做参照)
    base = {}
    p = os.path.join(ROOT, "marketplace-catalog.json")
    if os.path.exists(p):
        for e in json.load(open(p, "r", encoding="utf-8")):
            base[int(e["Id"])] = e

    entries = []
    for sku, item, price, days, votes in rows:
        e = base.get(sku)
        if e:
            entries.append(dict(e))
            continue
        entries.append({
            "Id": sku, "Item": item,
            "Currency": cur.get(sku, 1),
            "Price": price, "Category": 0,
            "Stackable": False, "Grant": 1, "SelectedDays": days,
        })
    # 把 exe 目录里独有、内存里没采到的也带上(不丢)
    have = set(x["Id"] for x in entries)
    for sku, e in base.items():
        if sku not in have:
            entries.append(dict(e))
    entries.sort(key=lambda x: int(x["Id"]))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, separators=(",", ":"))
    print("导出 %d 条 -> %s" % (len(entries), OUT))
    print("  其中内存新增(不在 exe): %d" % (len(rows) - sum(1 for s, *_ in rows if s in base)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
