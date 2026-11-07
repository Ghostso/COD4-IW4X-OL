# -*- coding: utf-8 -*-
"""015: locate module data inside the large dumps by content search."""
import sys

CANDS = [
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_low.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_zone.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_wide.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_devmap.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_map.bin",
]
NEEDLES = [b"mmbook accepted", b"mmbook timedout"]

for path in CANDS:
    try:
        d = open(path, "rb").read()
    except OSError as e:
        print("%s OPEN FAIL %s" % (path, e))
        continue
    print("=" * 70)
    print("%s size=0x%X" % (path, len(d)))
    for n in NEEDLES:
        i = d.find(n)
        hits = []
        while i >= 0 and len(hits) < 4:
            hits.append(i)
            i = d.find(n, i + 1)
        for h in hits:
            base = 0xDC69B0 - h if n == NEEDLES[0] else 0xDC69D4 - h
            print("   %-18s @0x%08X  => module base would be 0x%08X"
                  % (n.decode(), h, base))
