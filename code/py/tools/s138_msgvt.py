#!/usr/bin/env python3
"""138: 枚举 vtable 区，解析 COL->ti->RTTI 名 + 相邻槽。
用法: s138_msgvt.py <lo> <hi>
每 4 字节，若值落在 COL 表(0xdf8xxx)且 COL+0xc->ti 是合法 type_info(.?A) 则视为一个 vtable 起点。
"""
import sys
import struct

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def u32(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f <= N - 4 else 0


def rtti_name(ti):
    f = ti - VA
    if not (0 <= f < N - 8):
        return None
    p = ti + 8  # type_info name is inline after 8-byte header
    e = d.find(b"\x00", p - VA)
    if e < 0:
        return None
    s = d[p - VA:e]
    try:
        t = s.decode("latin1")
    except Exception:
        return None
    if t.startswith(".?A"):
        return t
    return None


def is_col(va):
    """COL->ti 合法?"""
    if not (VA <= va < VA + N):
        return None
    ti = u32(va + 0xC)
    nm = rtti_name(ti)
    return nm


lo = int(sys.argv[1], 0)
hi = int(sys.argv[2], 0)
for a in range(lo, hi, 4):
    v = u32(a)
    nm = is_col(v)
    if nm:
        # 读后面 8 个槽
        slots = [u32(a + 4 + i * 4) for i in range(4)]
        print("vtable 0x%08X COL=0x%08X  %s" % (a, v, nm))
        for i, s in enumerate(slots):
            if VA <= s < VA + N and 0x400000 <= s < 0xD00000 and u32(s - 1) & 0xFF == 0xCC or True:
                print("    vf%d = 0x%08X" % (i, s))
