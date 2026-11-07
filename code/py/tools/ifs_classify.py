#!/usr/bin/env python3
"""把 974 个 .ifs 按「结构类型」分类：
   L = 纯清单（无 IWff，清单占满）
   F = 清单 + IWff 载荷
   ? = 其它
对每类统计尺寸、熵、清单行数、IWff 偏移。
"""
import os
import struct
import sys
from collections import Counter


def main():
    root = sys.argv[1]
    files = sorted(f for f in os.listdir(root) if f.endswith(".ifs"))
    cls = Counter()
    sizes = {"L": Counter(), "F": Counter(), "?": Counter()}
    for fn in files:
        p = os.path.join(root, fn)
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            head = f.read(0x4000)
        if head[:4] != b"nifs":
            cls["bad"] += 1
            continue
        i = head.find(b"IWff")
        tbl0 = struct.unpack_from("<Q", head, 0x0C)[0]
        if i >= 0:
            cls["F"] += 1
            sizes["F"][size] += 1
        else:
            cls["L"] += 1
            sizes["L"][size] += 1

    print("类别统计:", dict(cls))
    for k in ("L", "F"):
        print("\n%s 类尺寸分布 (top 10):" % k)
        for s, n in sizes[k].most_common(10):
            print("   %-10d x%d" % (s, n))


if __name__ == "__main__":
    main()
