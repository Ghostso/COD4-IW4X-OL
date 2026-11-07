#!/usr/bin/env python3
"""s138_fileoff: convert VA<->file offset and dump bytes.
Usage: python -I tools/s138_fileoff.py <VA> [len]
"""
import sys
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = open(E, "rb").read()
n = int(sys.argv[1], 0)
if n >= VA:
    print("fileoff=0x%X" % (n - VA))
    if len(sys.argv) > 2:
        ln = int(sys.argv[2], 0)
        b = d[n - VA:n - VA + ln]
        print(b.hex())
else:
    print("VA=0x%X" % (n + VA))
