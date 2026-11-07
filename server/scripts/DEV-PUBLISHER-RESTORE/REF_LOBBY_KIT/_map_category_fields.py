# -*- coding: utf-8 -*-
"""用大量样本, 找出内存记录里哪个字段 == exe 目录的 Category。

做法: 收集所有"记录 item 在 exe 目录里有唯一 Category"的样本,
      统计每个偏移上的值与该 Category 的吻合率。
"""
import json
import os
import struct
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
MAIN = os.path.join(MEMDIR, "r_259D0000_06400000.bin")
STRIDE = 0x60
NONE = 0xFFFFFFFF


def main():
    cat = json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                         "r", encoding="utf-8"))
    by_item = defaultdict(set)
    for e in cat:
        by_item[int(e["Item"])].add(int(e["Category"]))
    # 只保留 Category 唯一的 item
    uniq = {k: next(iter(v)) for k, v in by_item.items() if len(v) == 1}
    print("exe 目录里 Category 唯一的 item: %d 个" % len(uniq))

    b = open(MAIN, "rb").read()
    recs = {}
    for off in range(0, len(b) - STRIDE, 4):
        sku = struct.unpack_from("<I", b, off)[0]
        if not (1 <= sku <= 500000):
            continue
        f = [struct.unpack_from("<I", b, off + k)[0]
             for k in range(0, STRIDE, 4)]
        if f[1] != 0:
            continue
        item = f[5]
        if item not in uniq:
            continue
        recs.setdefault(item, f)
    print("其中在内存记录里能找到的: %d 个" % len(recs))
    print()

    # 对每个偏移, 统计有多少记录的该偏移 == Category
    print("%-8s %-14s %-14s" % ("偏移", "==Category", "取值分布(top3)"))
    for k in range(24):
        eq = 0
        dist = Counter()
        for item, f in recs.items():
            if f[k] == uniq[item]:
                eq += 1
            dist[f[k]] += 1
        if eq > len(recs) * 0.3:
            print("+0x%02X    %-14d %s"
                  % (k * 4, eq, dist.most_common(3)))
    print()
    # 顺带看 Category 的分布
    print("样本的 Category 分布:",
          Counter(uniq[i] for i in recs).most_common())
    return 0


if __name__ == "__main__":
    sys.exit(main())
