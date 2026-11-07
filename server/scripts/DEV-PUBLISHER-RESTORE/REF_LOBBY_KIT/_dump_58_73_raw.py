# -*- coding: utf-8 -*-
"""打印 sku=58/73/31181/31184 的原始记录, 找形态判据。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(ROOT, "mem_linear", "r_259D0000_06400000.bin")
STRIDE = 0x60


def main():
    b = open(MAIN, "rb").read()
    for sku in (58, 73, 31181, 31184, 37251, 16350):
        pat = struct.pack("<I", sku)
        print("=" * 78)
        print("sku=%d" % sku)
        i = 0
        n = 0
        while n < 6:
            i = b.find(pat, i)
            if i < 0:
                break
            if i + STRIDE <= len(b):
                f = [struct.unpack_from("<I", b, i + k)[0] for k in range(0, STRIDE, 4)]
                if f[1] == 0:
                    print("  0x%08X  " % i + " ".join("%08X" % v for v in f[:8]))
                    print("              +04=%d +08=%d +0C=%d +10=%d +14=%d +18=%d +1C=%d"
                          % (f[1], f[2], f[3], f[4], f[5], f[6], f[7]))
                    n += 1
            i += 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
