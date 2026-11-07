#!/usr/bin/env python3
"""s138_dumptbl: 通用 dump 一段 VA 的 dword 流, 注释字符串/代码."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000

def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

def cstr(va, ml=80):
    o = va - VA
    if not (0 <= o < N - 1): return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2: return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None

lo = int(sys.argv[1], 0); hi = int(sys.argv[2], 0)
for va in range(lo, hi, 4):
    v = u32(va)
    note = ""
    if v and 0x401000 <= v < 0x401000 + 0x8a689a: note = " CODE"
    elif v:
        s = cstr(v)
        if s: note = " STR %r" % s
        elif v < 0x200: note = " (=%d)" % v
    print("  0x%08X: 0x%08X%s" % (va, v or 0, note))
