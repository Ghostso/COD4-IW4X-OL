#!/usr/bin/env python3
"""137: dump image regions as hex+ascii, and report image size."""
import sys

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
print("image size = 0x%X (%d bytes); VA span 0x%08X..0x%08X" %
      (N, N, VA, VA + N))


def dump(va, ln):
    f = va - VA
    if f < 0 or f + ln > N:
        print("  <oob 0x%08X>" % va)
        return
    print("--- @0x%08X (%d) ---" % (va, ln))
    for r in range(0, ln, 16):
        c = d[f + r:f + r + 16]
        print("  %08X  %-47s  %s" % (
            va + r, c.hex(" "),
            "".join(chr(x) if 32 <= x < 127 else "." for x in c)))


for a in sys.argv[1:]:
    parts = a.split(":")
    va = int(parts[0], 0)
    ln = int(parts[1], 0) if len(parts) > 1 else 0x100
    dump(va, ln)
    print()
