#!/usr/bin/env python3
"""s138_srpc_scan: scan region for records of stride 0x25D0 (or 0x25D0)
looks for svc/task dwords at +0x28/+0x2C and fn at +0x25D0-?
Just dumps candidate records anchored at given start.
Usage: python -I tools/s138_srpc_scan.py [startVA] [count]
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def u8(va):
    o = va - VA
    return d[o] if 0 <= o < N else None


def u32(va):
    o = va - VA
    if 0 <= o <= N - 4:
        return struct.unpack_from("<I", d, o)[0]
    return None


start = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0xE374638
cnt = int(sys.argv[2], 0) if len(sys.argv) > 2 else 4
S = 0x25D0
for k in range(cnt):
    base = start + k * S
    print("rec %d base 0x%08X" % (k, base))
    for off in (0, 4, 8, 0xC, 0x10, 0x14, 0x18, 0x19, 0x28, 0x2C, 0x30, 0x38, 0x40,
                0x400, 0x25C0, 0x25C8, 0x25D0 - 8):
        print("   +0x%04X = 0x%08X  b=%s" % (off, u32(base + off) or 0, u8(base + off)))
