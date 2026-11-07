# -*- coding: utf-8 -*-
"""找 callsign ref -> itemID 的映射表。

已知:
  - ref 形如 pcb_amorphous01 (4784 个)
  - itemID 是数字(如 22381/22384)
  - 客户端用 CallSignObj/cardXxxItemID 判断拥有

思路: 在内存里找 "ref 字符串 + 邻近的 u32" 的结构。
"""
import os
import re
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
REF_RE = re.compile(rb"\b(pcb|pci|pct|pcf|pcab|pcai|pcaf|pcn|cnc)_([A-Za-z0-9_]{2,60})\x00")


def main():
    # 统计: 每个 ref 后面 4/8/12 字节处的 u32 值, 看是否集中在小范围
    dist = {4: Counter(), 8: Counter(), 12: Counter(), -4: Counter()}
    samples = []
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
            end = m.end()
            for off in dist:
                j = end + off
                if 0 <= j <= len(b) - 4:
                    v = struct.unpack_from("<I", b, j)[0]
                    if 1 <= v <= 500000:
                        dist[off][v] += 1
                        if len(samples) < 20 and off == 4:
                            samples.append((m.group(0).decode("latin1"),
                                            v, fn, m.start()))
    print("扫 %d 个区" % files)
    for off in sorted(dist):
        c = dist[off]
        print()
        print("ref 结尾 %+d 字节处的 u32 (1..500000): %d 个不同值, top 12:"
              % (off, len(c)))
        for v, n in c.most_common(12):
            print("    %-8d x%d" % (v, n))
    print()
    print("样例(ref, +4 处的值):")
    for s, v, fn, off in samples:
        print("  %-34s -> %-8d  (%s @0x%X)" % (s, v, fn, off))
    return 0


if __name__ == "__main__":
    sys.exit(main())
