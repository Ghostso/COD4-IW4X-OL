# -*- coding: utf-8 -*-
"""找 SKU -> Item 的映射表。

思路: 对一批"同时在运行时记录和 exe 目录里"的 SKU, 在内存里搜索
      SKU 的 u32 与它的 exe.Item 的 u32 **在同一个窗口内共现**的位置。
      如果存在一张映射表, 相对偏移会高度一致。
"""
import json
import os
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
CAT = os.path.join(ROOT, "marketplace-catalog.json")
WINDOW = 0x400


def main():
    cat = {int(e["Id"]): e for e in json.load(open(CAT, "r", encoding="utf-8"))}

    # 用 exe 目录里的 sku 做搜索(它们本身就是合法 sku, 且 Item 已知)
    samples = []
    for sku, e in sorted(cat.items()):
        item = int(e["Item"])
        if 1 <= sku <= 500000 and 1 <= item <= 500000 and sku != item:
            samples.append((sku, item))
    print("候选样本 (sku, exe.Item): %d" % len(samples))

    offsets = Counter()
    examples = []
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
        for sku, item in samples:
            sp = struct.pack("<I", sku)
            ip = struct.pack("<I", item)
            i = 0
            while True:
                i = b.find(sp, i)
                if i < 0:
                    break
                lo = max(0, i - WINDOW)
                hi = min(len(b), i + WINDOW)
                j = b.find(ip, lo, hi)
                if j >= 0:
                    d = j - i
                    offsets[d] += 1
                    if len(examples) < 40:
                        examples.append((fn, i, d, sku, item))
                i += 4

    print("扫描 %d 个内存区" % files)
    print()
    print("共现相对偏移 top 20 (offset, 次数):")
    for d, n in offsets.most_common(20):
        print("  %+6d (0x%X) : %d" % (d, d & 0xFFFFFFFF, n))
    print()
    print("样例:")
    for fn, i, d, sku, item in examples[:25]:
        print("  %s 0x%08X  sku=%-7d item=%-7d  d=%+d" % (fn, i, sku, item, d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
