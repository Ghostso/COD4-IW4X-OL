# -*- coding: utf-8 -*-
"""在**所有** IIPS 包里找 callsign 表(不管哪个包)。

直接在字节流里搜 callsignTitle / callsignNameplate 等表名,
找到就把所在包和偏移记下来。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IIPS = os.path.abspath(os.path.join(ROOT, "..", "COD OL", "IIPS", "IIPSDownload"))
OUT = os.path.join(ROOT, "mkt_assets")

NEEDLES = [b"callsignTitle", b"callsignBackground", b"callsignIcon",
           b"callsignFrame", b"callsignNameplate", b"item_cnc",
           b"badgeTable", b"rankIconTable"]


def main():
    names = sorted(os.listdir(IIPS))
    packs = [n for n in names if n.lower().endswith(".ifs")]
    print("扫描 %d 个包, 找 callsign 表名..." % len(packs))
    found = {}
    for i, n in enumerate(packs, 1):
        p = os.path.join(IIPS, n)
        try:
            sz = os.path.getsize(p)
            if sz > 800 * 1024 * 1024:
                continue
            b = open(p, "rb").read()
        except Exception:
            continue
        for nd in NEEDLES:
            if nd in b:
                off = b.find(nd)
                found.setdefault(nd.decode(), []).append((n, off, sz))
        if i % 100 == 0:
            print("  ... %d/%d" % (i, len(packs)))

    print()
    print("== 结果 ==")
    for k in sorted(found):
        print("%s: %d 个包" % (k, len(found[k])))
        for n, off, sz in found[k][:8]:
            print("   %-58s off=0x%08X size=%d" % (n, off, sz))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "callsign_table_locations.txt"), "w",
              encoding="utf-8") as f:
        for k in sorted(found):
            for n, off, sz in found[k]:
                f.write("%s\t%s\t0x%08X\t%d\n" % (k, n, off, sz))
    print()
    print("已写出 callsign_table_locations.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
