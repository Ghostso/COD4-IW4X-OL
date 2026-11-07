#!/usr/bin/env python3
"""s138_settype: find `mov byte ptr [eax],imm8` (c6 00 XX) / `[ecx]` (c6 01 XX)
in a VA range, which are the "out event type" writes in the connection reader.
Usage: python -I tools/s138_settype.py <lo> <hi>
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

lo = int(sys.argv[1], 0) - VA
hi = int(sys.argv[2], 0) - VA
for pat, reg in ((b"\xc6\x00", "[eax]"), (b"\xc6\x01", "[ecx]"), (b"\xc6\x02", "[edx]")):
    i = lo
    while True:
        i = d.find(pat, i, hi)
        if i < 0:
            break
        print("0x%08X  mov byte ptr %s, 0x%02X" % (VA + i, reg, d[i + 2]))
        i += 1
