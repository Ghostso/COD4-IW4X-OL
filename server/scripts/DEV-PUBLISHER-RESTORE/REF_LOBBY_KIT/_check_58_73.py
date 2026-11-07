# -*- coding: utf-8 -*-
"""核对 sku=58 / 73 的所有候选记录, 确认提取值不是误报。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
STRIDE = 0x60


def main():
    b = open(MAIN, "rb").read()
    for sku in (58, 73, 98, 120, 242):
        pat = struct.pack("<I", sku)
        print("=" * 72)
        print("sku=%d" % sku)
        i = 0
        while True:
            i = b.find(pat, i)
            if i < 0:
                break
            if i + STRIDE <= len(b):
                f = [struct.unpack_from("<I", b, i + k)[0] for k in range(0, STRIDE, 4)]
                if f[1] == 0 and f[4] == 0:
                    print("  0x%08X  +04=%-4d +08=%-10d +0C=%-10d +10=%-4d +14=%-10d +1C=%-10d"
                          % (i, f[1], f[2], f[3], f[4], f[5], f[7]))
            i += 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
