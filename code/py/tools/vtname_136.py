#!/usr/bin/env python3
"""136 卷工具 G: 给定 vtable VA, 按 MSVC 布局取类名.
vftable[-1] = COL(CompleteObjectLocator); COL+0x0C -> type_info; name = *(type_info+0x0C)+8
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def rd(va):
    f = va - VA
    if not (0 <= f < N - 4):
        return None
    return struct.unpack_from("<I", d, f)[0]


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def name_of(vtable_va):
    col = rd(vtable_va - 4)
    if not col or not (VA <= col < VA + N):
        return "COL=%r 非法" % col
    ti = rd(col + 0x0C)
    if not ti or not (VA <= ti < VA + N):
        return "COL=0x%08X type_info=%r 非法" % (col, ti)
    host = rd(ti + 0x0C)
    nm = cstr(ti + 8)
    nm2 = cstr(host + 8) if host and VA <= host < VA + N else None
    return "COL=0x%08X ti=0x%08X  ti+8=%r  (host=0x%08X ->%r)" % (
        col, ti, nm, host or 0, nm2)


for a in sys.argv[1:]:
    vt = int(a, 0)
    print("vtable 0x%08X -> %s" % (vt, name_of(vt)))
