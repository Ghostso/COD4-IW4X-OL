# -*- coding: utf-8 -*-
"""015: find pointer tables (IAT-like) inside image_best.bin.

A slot is 'foreign' if it holds a dword that is not inside the image and is
a plausible user-space code pointer (kernel32/ws2_32 style).
"""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END  # noqa

HDRLEN = 0x1000

LO = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x60000000
HI = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x80000000
MINRUN = int(sys.argv[3]) if len(sys.argv) > 3 else 4


def is_foreign(v):
    if BASE <= v < END:
        return False
    if LO <= v < HI:
        return True
    return False


runs = []
cur = None
for off in range(HDRLEN, len(DATA) - 4, 4):
    v = struct.unpack_from("<I", DATA, off)[0]
    if is_foreign(v):
        if cur is None:
            cur = [off, off]
        else:
            cur[1] = off
    else:
        if cur is not None:
            runs.append(cur)
            cur = None
if cur:
    runs.append(cur)

runs = [r for r in runs if (r[1] - r[0]) // 4 + 1 >= MINRUN]
print("runs>=%d : %d" % (MINRUN, len(runs)))
for a, b in runs:
    n = (b - a) // 4 + 1
    print("  VA 0x%08X .. 0x%08X  (%d slots)" % (BASE + a, BASE + b + 3, n))
    if n <= 40 or "-v" in sys.argv:
        for k in range(n):
            v = struct.unpack_from("<I", DATA, a + 4 * k)[0]
            print("      +0x%03X  0x%08X" % (4 * k, v))
