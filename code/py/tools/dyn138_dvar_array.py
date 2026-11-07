#!/usr/bin/env python3
"""138 · 整表挖 dvar_t：在 dump 的某区间里找所有"指向静态镜像内标识符串"的字，
推断记录步进，输出 (name, flags, type, value) 全表。

用法: python -X utf8 tools\dyn138_dvar_array.py <dumpdir> [lo hi]
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IMG = r"E:\codol_re\client_image_20261027.bin"
VA0 = 0x400000
dump = sys.argv[1]
lo = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x0810E000
hi = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x0811B200

img = open(IMG, "rb").read()
NI = len(img)


def name_at(va, maxlen=48):
    f = va - VA0
    if not (0 <= f < NI):
        return None
    e = img.find(b"\x00", f)
    if e < 0 or e - f > maxlen or e == f:
        return None
    s = img[f:e]
    if not all(32 <= c < 127 for c in s):
        return None
    return s.decode("latin1")


regs = []
with open(os.path.join(dump, "regions.txt"), encoding="utf-8", errors="replace") as f:
    for ln in f:
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split()
        if len(p) >= 3:
            regs.append((int(p[0], 16), int(p[1], 16), p[2]))

rows = []
for base, size, fn in regs:
    if base + size <= lo or base >= hi:
        continue
    data = open(os.path.join(dump, "mem", fn), "rb").read()
    s = max(lo, base)
    e = min(hi, base + size)
    for off in range(s - base, e - base - 4, 1):
        w = struct.unpack_from("<I", data, off)[0]
        if VA0 <= w < VA0 + NI:
            nm = name_at(w)
            if nm and (nm[0].isalpha() or nm[0].isdigit()) and len(nm) >= 1:
                addr = base + off
                def u32(o):
                    j = off - 0 + o
                    return struct.unpack_from("<I", data, j)[0] if j + 4 <= len(data) else None
                rows.append((addr, nm, u32(0x04), u32(0x08), u32(0x0C)))

# 去重 + 推断步进
rows.sort()
print("命中 %d 个候选" % len(rows))
if rows:
    gaps = {}
    for a, b in zip(rows, rows[1:]):
        d = b[0] - a[0]
        gaps[d] = gaps.get(d, 0) + 1
    top = sorted(gaps.items(), key=lambda kv: -kv[1])[:8]
    print("相邻步进 top:", top)
print()
print("%-10s %-26s %-9s %-6s %s" % ("dvar_t@", "name", "flags", "type", "value"))
for addr, nm, fl, ty, va in rows:
    sv = "%08X" % va if va is not None else "?"
    note = ""
    if ty == 1 and va is not None:
        note = " f32=%r" % struct.unpack("<f", struct.pack("<I", va))[0]
    if ty == 7 and va is not None:
        st = name_at(va, 64)
        note = " str=%r" % st
    print("%08X   %-26s %08X  %6s %s%s"
          % (addr, nm, fl if fl is not None else 0, ty, sv, note))
