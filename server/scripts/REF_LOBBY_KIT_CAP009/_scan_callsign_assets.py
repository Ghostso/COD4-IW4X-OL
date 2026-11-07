# -*- coding: utf-8 -*-
"""在已抽出的资源路径清单里找 Callsign 相关资源(表/图标)。"""
import csv
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(ROOT, "mkt_assets", "mkt_assets_table.csv")
PAT = re.compile(r"callsign|badge|emblem|nameplate|pcb_|pci_|pcab_|pcai_|pcf_|pcaf_|pcn_|cnc_|pct_", re.I)


def main():
    rows = list(csv.DictReader(open(TABLE, "r", encoding="utf-8-sig")))
    print("资源表条目: %d" % len(rows))
    hits = [r for r in rows if PAT.search(r.get("path", ""))]
    print("Callsign 相关资源: %d" % len(hits))
    print()
    print("按 kind 统计:", Counter(r.get("kind", "") for r in hits).most_common(10))
    print("按前缀统计:", Counter(r.get("prefix", "") for r in hits).most_common(15))
    print()
    print("非图片的条目(可能是表):")
    n = 0
    for r in hits:
        p = r.get("path", "")
        if not p.lower().endswith((".iwi", ".dds", ".png", ".jpg")):
            print("  %s" % p)
            n += 1
            if n >= 60:
                break
    print("共 %d 个" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
