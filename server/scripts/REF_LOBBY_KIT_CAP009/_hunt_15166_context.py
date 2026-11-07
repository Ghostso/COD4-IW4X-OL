# -*- coding: utf-8 -*-
"""在内存里搜 item=15166 的所有出现位置, 看附近有没有 callsign ref。

15166 是我们实际买到的名片(背景) item ID。
如果客户端要用它显示, 必须能从某个表查到 ref。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
REF_RE = re.compile(rb"\b(pcb|pci|pct|pcf|pcab|pcai|pcaf|pcn|cnc|bdg)_[A-Za-z0-9_]{2,60}")
TARGETS = (15166, 22381, 22384, 29892)
WIN = 0x2000


def main():
    for t in TARGETS:
        print("=" * 76)
        print("item %d" % t)
        tp = struct.pack("<I", t)
        total = 0
        hits = []
        for fn in sorted(os.listdir(MEMDIR)):
            p = os.path.join(MEMDIR, fn)
            if not os.path.isfile(p):
                continue
            try:
                b = open(p, "rb").read()
            except Exception:
                continue
            i = 0
            while True:
                i = b.find(tp, i)
                if i < 0:
                    break
                total += 1
                lo = max(0, i - WIN)
                hi = min(len(b), i + WIN)
                m = REF_RE.search(b, lo, hi)
                if m:
                    hits.append((fn, i, m.group(0).decode("latin1"),
                                 m.start() - i))
                i += 4
        print("  总出现 %d 次, 附近(±0x%X)有 callsign ref 的: %d 次"
              % (total, WIN, len(hits)))
        for fn, i, ref, d in hits[:15]:
            print("    %s @0x%X  ref=%-30s d=%+d" % (fn, i, ref, d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
