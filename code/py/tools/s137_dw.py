#!/usr/bin/env python3
"""137: 按 VA 打印若干 dword (VA = file + 0x400000)."""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

for a in sys.argv[1:]:
    va = int(a, 0)
    f = va - VA
    if not (0 <= f < N - 32):
        print("0x%08X: 越界" % va)
        continue
    ws = struct.unpack_from("<8I", d, f)
    print("0x%08X: " % va + "  ".join("0x%08X" % w for w in ws))
