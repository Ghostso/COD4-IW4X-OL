# -*- coding: utf-8 -*-
"""在**全部** .ifs 包里找 .csv 路径 —— 之前的扫描只覆盖了 marketplace 包。

重点找 coMarketplace*.csv / unlockFlags.csv。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IIPS = os.path.abspath(os.path.join(ROOT, "..", "COD OL", "IIPS", "IIPSDownload"))
PAT = re.compile(rb"[A-Za-z0-9_/\.\-]{3,80}\.csv")
TARGET = re.compile(rb"comarketplace|marketplace\.json|unlockflags", re.I)


def main():
    if not os.path.isdir(IIPS):
        print("缺 %s" % IIPS)
        return 1
    names = sorted(n for n in os.listdir(IIPS) if n.lower().endswith(".ifs"))
    print("扫 %d 个 .ifs" % len(names))
    csv_hits = {}
    target_hits = []
    for i, n in enumerate(names, 1):
        p = os.path.join(IIPS, n)
        try:
            if os.path.getsize(p) > 900 * 1024 * 1024:
                continue
            b = open(p, "rb").read()
        except Exception:
            continue
        for m in PAT.finditer(b):
            s = m.group(0).decode("latin1")
            csv_hits.setdefault(s, []).append(n)
        if TARGET.search(b):
            for m in TARGET.finditer(b):
                target_hits.append((n, m.start(), b[m.start():m.start() + 40]))
        if i % 200 == 0:
            print("  ... %d/%d, 已见 %d 个唯一 .csv 名"
                  % (i, len(names), len(csv_hits)))
    print()
    print("唯一 .csv 名 %d 个" % len(csv_hits))
    for s in sorted(csv_hits)[:120]:
        print("  %-52s %s" % (s, csv_hits[s][:2]))
    print()
    print("含 comarketplace/marketplace.json/unlockflags 的位置: %d" % len(target_hits))
    for n, off, raw in target_hits[:30]:
        print("  %-46s @0x%X %r" % (n, off, raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
