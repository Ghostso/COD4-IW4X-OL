#!/usr/bin/env python3
"""137: find all dwords whose value lies in [lo,hi) -> locations."""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def cstr(va, maxlen=60):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    try:
        return d[f:e].decode("latin1")
    except Exception:
        return None


lo = int(sys.argv[1], 0)
hi = int(sys.argv[2], 0)
hits = []
for i in range(0, N - 4):
    v = struct.unpack_from("<I", d, i)[0]
    if lo <= v < hi:
        hits.append((VA + i, v))
print("dwords in [0x%08X,0x%08X): %d" % (lo, hi, len(hits)))
for loc, v in hits[:400]:
    ctx = d[max(0, loc - VA - 6):loc - VA + 6]
    print("  0x%08X -> 0x%08X  %r  ctx=%s" % (
        loc, v, cstr(v, 40) or "", ctx.hex(" ")))
