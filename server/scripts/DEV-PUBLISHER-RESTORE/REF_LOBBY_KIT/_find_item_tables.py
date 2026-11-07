# -*- coding: utf-8 -*-
"""找 mp/item_<prefix>.csv 这类"物品表" —— 里面才有 itemID。

exe 字符串表里的证据:
    CONSUMABLE_ITEM | mp/item_%s.csv | pcb | playercard background |
    SF_UI_ITEM_MENU_PCB | mp/callsignBackground.csv | bdg | ...

即: 每个前缀( pcb/pci/pct/pcf/bdg/cnc )都有一张 mp/item_<prefix>.csv,
里面是 ref -> itemID 的映射。
"""
import os
import re
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")


def main():
    pats = [b"item_pcb", b"item_pci", b"item_pct", b"item_pcf", b"item_bdg",
            b"item_cnc", b"item_pcab", b"item_pcai", b"item_pcaf",
            b"mp/item_"]
    found = Counter()
    where = {}
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for pat in pats:
            n = b.count(pat)
            if n:
                found[pat.decode()] += n
                where.setdefault(pat.decode(), []).append((fn, b.find(pat)))

    print("命中统计:")
    for k, v in found.most_common():
        print("  %-12s %d" % (k, v))
    print()
    for k, lst in where.items():
        print("== %s ==" % k)
        for fn, off in lst[:5]:
            b = open(os.path.join(MEMDIR, fn), "rb").read()
            lo = max(0, off - 120)
            hi = min(len(b), off + 200)
            strs = re.findall(rb"[ -~]{4,120}", b[lo:hi])
            print("  %s @0x%X" % (fn, off))
            for s in strs[:12]:
                print("      %s" % s.decode("latin1"))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
