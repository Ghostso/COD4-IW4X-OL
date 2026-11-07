#!/usr/bin/env python3
"""138: dump dwords with ascii hint"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()
VA = 0x400000
N = len(d)


def cstr(va, mx=60):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > mx:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def dw(start, n):
    f = start - VA
    for i in range(0, n, 4):
        v = struct.unpack_from("<I", d, f + i)[0]
        extra = ""
        if 0x401000 <= v < 0x1400000:
            s = cstr(v)
            if s:
                extra = "  ; '%s'" % s
        print("  0x%08X  %08X%s" % (start + i, v, extra))


if __name__ == "__main__":
    s = int(sys.argv[1], 0)
    n = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x40
    dw(s, n)
