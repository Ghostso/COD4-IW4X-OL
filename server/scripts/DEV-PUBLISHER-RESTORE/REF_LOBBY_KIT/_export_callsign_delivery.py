# -*- coding: utf-8 -*-
"""出名片/称号的最终交付表(可读 Markdown + 机器可读 CSV)。

数据源: mkt_assets/callsign_all.txt (全盘扫描 37 个完整版 marketplace 包 + IIPS)
"""
import csv
import os
import re
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "mkt_assets")

CATEGORY = {
    "pcb": "名片背景",
    "pci": "头像图标",
    "pcab": "名片动态背景",
    "pcai": "名片动态图标",
    "pcf": "名片边框",
    "pcaf": "名片动态边框",
    "pcn": "名片名称",
    "pca": "名片(其他)",
    "cnc": "解锁类名片",
    "bdg": "肩章/徽章",
    "pct": "称号",
}


def clean(name):
    n = re.sub(r"_item_icon.*$", "", name)
    n = re.sub(r"_lod\d+.*$", "", n)
    return n


def main():
    src = os.path.join(SRC, "callsign_all.txt")
    if not os.path.exists(src):
        print("缺 %s" % src)
        return 1
    items = {}
    for ln in open(src, encoding="utf-8"):
        parts = ln.rstrip("\n").split("\t")
        if not parts or not parts[0]:
            continue
        raw = parts[0]
        cnt = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        pref = raw.split("_")[0]
        nm = clean(raw)
        d = items.setdefault(nm, {"name": nm, "prefix": pref,
                                  "category": CATEGORY.get(pref, "其他"),
                                  "raw": raw, "files": 0})
        d["files"] += cnt

    out = os.path.join(SRC, "callsign_delivery.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["name", "prefix", "category", "raw_name"])
        for k in sorted(items, key=lambda x: (items[x]["category"], x)):
            v = items[k]
            w.writerow([v["name"], v["prefix"], v["category"], v["raw"]])

    cat = Counter(v["category"] for v in items.values())
    md = os.path.join(SRC, "callsign_delivery.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# 名片 / 称号 —— 本地交付清单\n\n")
        f.write("> 数据源: 37 个完整版 `common_marketplace` 包(9.4 GB) + `COD OL\\IIPS` 全盘扫描\n\n")
        f.write("| 类别 | 数量 |\n|---|---|\n")
        for k, v in cat.most_common():
            f.write("| %s | %d |\n" % (k, v))
        f.write("| **合计** | **%d** |\n\n" % len(items))
        f.write("## 明细\n\n")
        for k in [c for c, _ in cat.most_common()]:
            f.write("### %s (%d)\n\n" % (k, cat[k]))
            names = sorted([x for x in items if items[x]["category"] == k])
            for x in names[:60]:
                f.write("- `%s`\n" % x)
            if len(names) > 60:
                f.write("- ...(共 %d 个)\n" % len(names))
            f.write("\n")

    print("写出 %s (%d 项)" % (out, len(items)))
    print("写出 %s" % md)
    for k, v in cat.most_common():
        print("  %-16s %5d" % (k, v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
