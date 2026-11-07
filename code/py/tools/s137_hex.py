#!/usr/bin/env python3
"""s137: hexdump 文件偏移范围."""
import sys

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
print("file size = 0x%X (%d)" % (len(d), len(d)))
lo = int(sys.argv[1], 0)
hi = int(sys.argv[2], 0)
for off in range(lo, min(hi, len(d)), 16):
    row = d[off:off + 16]
    print("0x%08X (VA 0x%08X)  %s  |%s|" % (
        off, off + VA, " ".join("%02x" % c for c in row),
        "".join(chr(c) if 32 <= c < 127 else "." for c in row)))
