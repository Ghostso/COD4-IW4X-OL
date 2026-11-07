#!/usr/bin/env python3
"""138: dump vtable slots. usage: s138_vt.py <vtableVA...>
prints [vt-4] (COL) and slots until non-code/0.
"""
import sys
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def u32(va):
    f = va - VA
    if 0 <= f <= N - 4:
        return struct.unpack_from("<I", d, f)[0]
    return None


def is_code(va):
    return va is not None and VA <= va < VA + N


for a in sys.argv[1:]:
    vt = int(a, 0)
    print("== vtable 0x%08X  COL[-1]=0x%08X" % (vt, u32(vt - 4) or 0))
    for i in range(20):
        p = u32(vt + i * 4)
        if not is_code(p):
            break
        print("   slot[%2d] VA 0x%08X" % (i, p))
