#!/usr/bin/env python3
"""s138_vtfull: dump vtable until a slot points outside .text or is 0."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000


def u32(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f <= N - 4 else None


def code(va):
    return va is not None and 0x401000 <= va < VA + N


for a in sys.argv[1:]:
    vt = int(a, 0)
    print("== vtable 0x%08X ==" % vt)
    i = 0
    while True:
        p = u32(vt + 4 * i)
        if not code(p):
            print("   stop at slot %d: 0x%08X" % (i, p or 0))
            break
        print("   slot[%3d] (+0x%03X) 0x%08X" % (i, 4 * i, p))
        i += 1
        if i > 400:
            break
