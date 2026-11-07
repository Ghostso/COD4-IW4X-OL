# -*- coding: utf-8 -*-
"""检查关键地址在内存转储里的覆盖情况。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
TARGETS = (0x239B120, 0x1E2D338, 0xE5C8C0, 0x49D3B0, 0x49D3D0,
           0x4A9330, 0x4A93E0, 0x49E160, 0x483DB0, 0x486B7E, 0x49CAA9)


def main():
    regions = []
    for fn in os.listdir(MEM):
        if not fn.startswith("r_") or not fn.endswith(".bin"):
            continue
        try:
            base = int(fn[2:10], 16)
            size = int(fn[11:19], 16)
        except Exception:
            continue
        regions.append((base, size, fn))
    regions.sort()
    print("regions: %d" % len(regions))
    if regions:
        print("  range 0x%08X .. 0x%08X"
              % (regions[0][0], regions[-1][0] + regions[-1][1]))
    print()
    for t in TARGETS:
        hit = None
        for base, size, fn in regions:
            if base <= t < base + size:
                hit = (fn, base)
                break
        if hit:
            print("  0x%08X -> %s off 0x%X" % (t, hit[0], t - hit[1]))
        else:
            print("  0x%08X -> NOT COVERED" % t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
