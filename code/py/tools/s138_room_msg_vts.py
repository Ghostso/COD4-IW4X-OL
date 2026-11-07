#!/usr/bin/env python3
"""s138: 枚举 dwRoomMessage 系列 vtable 家族 (3-dword 步进: [COL][serialize][deserialize]).
用法: s138_room_msg_vts.py <lo> <hi>
COL 判定: COL+0xC -> type_info, ti+8 以 .?A 开头且含 dwRoomMessage.
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def u32(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f <= N - 4 else None


def rtti(ti):
    f = ti - VA
    if not (0 <= f < N - 8):
        return None
    p = ti + 8
    e = d.find(b"\x00", p - VA)
    if e < 0:
        return None
    s = d[p - VA:e]
    try:
        t = s.decode("latin1")
    except Exception:
        return None
    return t if t.startswith(".?A") else None


def col_name(col):
    ti = u32(col + 0xC)
    if not ti:
        return None
    nm = rtti(ti)
    if nm and ("dwRoomMessage" in nm):
        return nm
    return None


lo = int(sys.argv[1], 0)
hi = int(sys.argv[2], 0)
a = lo
while a < hi:
    col = u32(a)
    nm = col_name(col) if col else None
    if nm:
        f0 = u32(a + 4)
        f1 = u32(a + 8)
        print("vftable[-1]=0x%08X  COL=0x%08X  %-45s  vf0=0x%08X  vf1=0x%08X"
              % (a, col, nm.replace(".?AV", "").replace(".?AU", "").replace("@@", ""), f0 or 0, f1 or 0))
        a += 12
    else:
        a += 4
