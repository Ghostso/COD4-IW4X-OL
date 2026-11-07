# -*- coding: utf-8 -*-
"""打印连号 SKU(37115..37118 / 28845..28849 / 17274..17282)的原始记录。

这些 SKU 的 Item 连号, 是最干净的样本, 用来确定记录的完整字段布局。
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
STRIDE = 0x60
TARGETS = (37115, 37116, 37117, 37118, 28845, 28847, 28849,
           17274, 17276, 17278, 17280, 17282)


def main():
    found = {}
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for off in range(0, len(b) - STRIDE, 4):
            sku = struct.unpack_from("<I", b, off)[0]
            if sku in TARGETS and sku not in found:
                f = [struct.unpack_from("<I", b, off + k)[0] for k in range(0, STRIDE, 4)]
                found[sku] = (fn, off, f)

    print("%-8s %-34s %-10s %s" % ("sku", "file", "off", "24 x u32"))
    for sku in TARGETS:
        if sku not in found:
            print("%-8d MISSING" % sku)
            continue
        fn, off, f = found[sku]
        print("%-8d %-34s 0x%08X %s"
              % (sku, fn, off, " ".join("%08X" % v for v in f)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
