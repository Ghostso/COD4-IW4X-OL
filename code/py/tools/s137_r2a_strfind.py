#!/usr/bin/env python3
"""s137 R2a: 在镜像里搜 UIClickCount / TIMESTAMP 相关字符串并给出 VA."""
import sys

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

needles = sys.argv[1:] or [
    "UIClickCount", "${TIMESTAMP}", "${TIMESTAMP_OFFSET", "Timestamp",
    "TIMESTAMP", "log_event", "UIClick", "UIPage",
]
for s in needles:
    nb = s.encode()
    print("=" * 70)
    print("NEEDLE %r (len %d)" % (s, len(nb)))
    off = 0
    hits = []
    while True:
        j = d.find(nb, off)
        if j < 0:
            break
        hits.append(j)
        off = j + 1
    print("  hits=%d" % len(hits))
    for j in hits[:40]:
        # context
        lo = max(0, j - 8)
        ctx = d[lo:j + len(nb) + 8]
        print("    file=0x%08X VA=0x%08X ctx=%r" % (j, j + VA, ctx))
