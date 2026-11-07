# -*- coding: utf-8 -*-
"""打印 105 个已点 SKU 在 r_259D0000 里的原始记录(24 x u32)。

已确认的干净布局(来自连号样本 37115..37118 / 28847..28849 / 17278..17282):
  +0x00 SKU
  +0x08 价格
  +0x14 物品 ID
  +0x1C 类别
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
UNKNOWN = os.path.join(ROOT, "unknown_skus.txt")
STRIDE = 0x60


def main():
    clicked = []
    for line in open(UNKNOWN, "r", encoding="utf-8", errors="replace"):
        m = re.match(r"\s*(\d+)", line)
        if m:
            clicked.append(int(m.group(1)))
    clicked = sorted(set(clicked))

    b = open(MAIN, "rb").read()
    print("%-8s %-10s %-8s %-8s %-8s %-8s %-8s" %
          ("sku", "+0x04", "+0x08", "+0x0C", "+0x10", "+0x14", "+0x1C"))
    print("-" * 70)
    for s in clicked:
        pat = struct.pack("<I", s)
        i = 0
        printed = False
        while True:
            i = b.find(pat, i)
            if i < 0:
                break
            if i + STRIDE <= len(b):
                f = [struct.unpack_from("<I", b, i + k)[0] for k in range(0, STRIDE, 4)]
                # 只看像"商品记录"的: +0x04 与 +0x10 为 0
                if f[1] == 0 and f[4] == 0 and f[5] != 0:
                    print("%-8d %-10d %-8d %-8d %-8d %-8d %-8d"
                          % (s, f[1], f[2], f[3], f[4], f[5], f[7]))
                    printed = True
                    break
            i += 4
        if not printed:
            print("%-8d (r_259D0000 里无干净记录)" % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
