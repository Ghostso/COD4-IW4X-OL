# -*- coding: utf-8 -*-
"""从内存区里抽出 callsign 表(名片背景/图标/称号/边框/肩章)。

已验证的结构(来自 r_48110000_0105A000.bin):
    <prefix>_<name>                      物品 ref
    PLAYERCARDS_<PREFIX>_<NAME>_NAME     显示名(localize key)
    PLAYERCARDS_<PREFIX>_<NAME>_DESC     描述
    <PREFIX>_<NAME>_ITEM_ICON            图标资源
    SCALEFORM_ASH/ITEMICONS/..._ITEM_ICON

前缀含义:
    pcb  -> mp/callsignBackground.csv   名片背景
    pci  -> mp/callsignIcon.csv         名片图标(徽章)
    pct  -> mp/callsignTitle.csv        称号
    pcf  -> mp/callsignFrame.csv        名片边框
    pcab -> 动态背景  pcai -> 动态图标  pcaf -> 动态边框
    pcn  -> 名称
    bdg  -> mp/badgeTable.csv           肩章
    cnc  -> mp/item_cnc.csv             消耗品

输出: mkt_assets/callsign_<prefix>.csv
"""
import csv
import os
import re
import sys
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
OUTDIR = os.path.join(ROOT, "mkt_assets")

REF_RE = re.compile(rb"\b(pcb|pci|pct|pcf|pcab|pcai|pcaf|pcn|bdg|cnc)_([A-Za-z0-9_]{2,60})\b")


def main():
    rows = OrderedDict()   # ref -> {ref,prefix,name}
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
        for m in REF_RE.finditer(b):
            pre = m.group(1).decode()
            name = m.group(2).decode()
            ref = "%s_%s" % (pre, name)
            rows.setdefault(ref, {"ref": ref, "prefix": pre, "name": name})

    print("扫 %d 个区, 唯一 ref %d 个" % (files, len(rows)))
    bypre = Counter(r["prefix"] for r in rows.values())
    print("按前缀:", dict(bpre := bypre.most_common()))

    os.makedirs(OUTDIR, exist_ok=True)
    groups = {}
    for r in rows.values():
        groups.setdefault(r["prefix"], []).append(r)
    total = 0
    for pre, lst in sorted(groups.items()):
        lst.sort(key=lambda x: x["name"])
        fn = os.path.join(OUTDIR, "callsign_%s.csv" % pre)
        with open(fn, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["ref", "prefix", "name"])
            w.writeheader()
            w.writerows(lst)
        total += len(lst)
        print("  %-6s %5d 条 -> %s" % (pre, len(lst), os.path.basename(fn)))
    print("合计 %d 条" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
