#!/usr/bin/env python3
"""扫全部 .ifs 里的 IWff 头部，统计 u32@+8 / +12 / +16 的取值分布。"""
import os
import struct
import sys
from collections import Counter


def main():
    root = sys.argv[1]
    files = sorted(f for f in os.listdir(root) if f.endswith(".ifs"))
    c8 = Counter()
    c12 = Counter()
    c16 = Counter()
    rows = []
    for fn in files:
        p = os.path.join(root, fn)
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            head = f.read(0x4000)
        i = head.find(b"IWff0100")
        if i < 0:
            continue
        if i + 24 > len(head):
            continue
        v8 = struct.unpack_from("<I", head, i + 8)[0]
        v12 = struct.unpack_from("<I", head, i + 12)[0]
        v16 = struct.unpack_from("<I", head, i + 16)[0]
        c8[v8] += 1
        c12[v12] += 1
        c16[v16] += 1
        rows.append((fn, size, i, v8, v12, v16))

    print("含 IWff 的文件数:", len(rows))
    print("\nu32@+8 (头内偏移 8):", c8.most_common(8))
    print("u32@+12           :", c12.most_common(8))
    print("u32@+16           :", c16.most_common(8))
    print("\n样本:")
    for r in rows[:20]:
        print("  %-58s size=%-10d iwff=%#06x  %d/%d/%d" % (
            r[0][:58], r[1], r[2], r[3], r[4], r[5]))


if __name__ == "__main__":
    main()
