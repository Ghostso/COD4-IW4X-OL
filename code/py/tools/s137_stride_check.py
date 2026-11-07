#!/usr/bin/env python3
"""137 结构性复核: 0x693DD0 字面量的间隙直方图 => 判定 AS 对象记录的真实步进(12 还是 17).
并列出 0xDC89xx 区域的记录与各记录前 4 字节(COL)解析出的名字."""
import struct
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def rd(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f < N - 4 else None


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def name_of_vt(vt):
    col = rd(vt - 4)
    if not col or not (VA <= col < VA + N):
        return "<no COL>"
    ti = rd(col + 0x0C)
    if not ti or not (VA <= ti < VA + N):
        return "<bad ti>"
    return cstr(ti + 8)


hits = []
pos = 0
pat = struct.pack("<I", 0x00693DD0)
while True:
    i = d.find(pat, pos)
    if i < 0:
        break
    hits.append(VA + i)
    pos = i + 1
print("0x00693DD0 字面量总数 =", len(hits))
gaps = Counter(b - a for a, b in zip(hits, hits[1:]))
print("相邻间隙 top:", gaps.most_common(8))

print("\n-- 0xDC89C0..0xDC8A40 区域 --")
for h in hits:
    if 0xDC89C0 <= h <= 0xDC8A40:
        vt = h            # vf0 位置 = vtable 首槽
        print("  vf0@0x%08X  vf1=0x%08X  next_dw=0x%08X  name=%-40s vf1名=%s" % (
            h, rd(h + 4), rd(h + 8), name_of_vt(vt),
            ("?" if not (VA <= (rd(h + 4) or 0) < VA + N) else "fn")))
