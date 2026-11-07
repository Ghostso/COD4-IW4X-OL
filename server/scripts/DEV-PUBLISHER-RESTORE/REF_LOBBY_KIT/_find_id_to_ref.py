# -*- coding: utf-8 -*-
"""反查: 已知 itemID(22381/22384) 附近有没有 callsign ref 字符串。

客户端要判断"是否拥有", 必须把 itemID 和 ref/表关联起来。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
REF_RE = re.compile(rb"\b(pcb|pci|pct|pcf|pcab|pcai|pcaf|pcn|cnc|bdg)_[A-Za-z0-9_]{2,60}")
IDS = (22381, 22384, 29892, 8270, 16339)
WIN = 0x1000


def main():
    hits = []
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
        for t in IDS:
            tp = struct.pack("<I", t)
            i = 0
            while True:
                i = b.find(tp, i)
                if i < 0:
                    break
                lo = max(0, i - WIN)
                hi = min(len(b), i + WIN)
                m = REF_RE.search(b, lo, hi)
                if m:
                    hits.append((t, fn, i, m.group(0).decode("latin1"),
                                 m.start() - i))
                i += 4

    print("扫 %d 个区" % files)
    print("ID 附近 ±0x%X 内出现 callsign ref 的次数: %d" % (WIN, len(hits)))
    seen = set()
    for t, fn, i, ref, d in hits:
        k = (t, ref)
        if k in seen:
            continue
        seen.add(k)
        print("  item %-6d  ref=%-34s d=%+d  (%s @0x%X)"
              % (t, ref, d, fn, i))
        if len(seen) > 60:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
