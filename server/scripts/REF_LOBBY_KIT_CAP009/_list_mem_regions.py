# -*- coding: utf-8 -*-
"""列出 mem_linear 所有区的基址 —— 用于解析内存里的指针。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")


def main():
    rows = []
    for fn in os.listdir(MEM):
        if not fn.startswith("r_") or not fn.endswith(".bin"):
            continue
        parts = fn[2:-4].split("_")
        if len(parts) != 2:
            continue
        try:
            base = int(parts[0], 16)
            size = int(parts[1], 16)
        except ValueError:
            continue
        rows.append((base, size, fn))
    rows.sort()
    print("共 %d 个区" % len(rows))
    print("含 0x4831xxxx 的区:")
    n = 0
    for base, size, fn in rows:
        if base <= 0x48310000 < base + size:
            print("  0x%08X .. 0x%08X  %s" % (base, base + size, fn))
            n += 1
    if n == 0:
        print("  (无)")
    print()
    print("0x48000000 附近的区:")
    for base, size, fn in rows:
        if 0x47F00000 <= base <= 0x48900000:
            print("  0x%08X .. 0x%08X  %-40s %d"
                  % (base, base + size, fn, size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
