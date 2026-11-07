#!/usr/bin/env python3
"""B7: dump 两个非 SF_Handler 局域类 (MyEventHandler / CAntiClientSinkImpl) 全串及邻串."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()


def cstr(va, maxlen=400):
    f = va - VA
    if not (0 <= f < len(d)):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    return d[f:e].decode("latin1")


for va in (0x00E6EF40, 0x00E6EFE4):
    print("VA=%08X  %s" % (va, cstr(va)))
    print()

# 邻域: 0xE6EE00..0xE6F080 区间的所有 null-terminated 串
lo, hi = 0x00E6EE00, 0x00E6F100
f = lo - VA
i = f
print("=== 邻域串 %08X..%08X ===" % (lo, hi))
while i < hi - VA:
    e = d.find(b"\x00", i)
    s = d[i:e]
    if len(s) >= 4 and all(32 <= c < 127 for c in s) and s.startswith(b".?A"):
        print("  0x%08X  %s" % (VA + i, s.decode("latin1")))
    i = e + 1
