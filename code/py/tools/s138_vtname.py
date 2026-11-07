#!/usr/bin/env python3
"""s138_vtname <vtableVA> [vtableVA...] : print MSVC RTTI name for a vtable address.
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def u32(va):
    o = va - VA
    if 0 <= o <= N - 4:
        return struct.unpack_from("<I", d, o)[0]
    return None


def cstr(va, ml=160):
    o = va - VA
    if not (0 <= o < N - 1):
        return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml:
        return None
    s = d[o:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


for arg in sys.argv[1:]:
    vt = int(arg, 0)
    col = u32(vt - 4)
    td = u32(col + 0x0C) if col else None
    nm = cstr(td + 8) if td else None
    print("vt 0x%08X  COL 0x%08X  td 0x%08X  name %r" % (vt, col or 0, td or 0, nm))
