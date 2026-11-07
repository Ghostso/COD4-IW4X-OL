#!/usr/bin/env python3
"""s138_hex <VA> <len> : hexdump with VA."""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
va = int(sys.argv[1], 0)
n = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x100
f = va - VA
for i in range(0, n, 16):
    chunk = d[f + i:f + i + 16]
    print("0x%08X  %-47s  %s" % (va + i, chunk.hex(" "),
                                 "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)))
