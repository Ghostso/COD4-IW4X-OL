#!/usr/bin/env python3
"""138 · 导出**活 dvar 表**（过滤假阳性）到文件。
记录 = 16 字节: {name_ptr@0, flags@4, type@8, value@0xC}
过滤: name 是标识符串 & flags <= 0x000F0000 & type <= 0xFF
用法: python -X utf8 tools\dyn138_dvar_dump.py <dumpdir> <out.txt> [lo hi]
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IMG = r"E:\codol_re\client_image_20261027.bin"
VA0 = 0x400000
dump = sys.argv[1]
out = sys.argv[2]
lo = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x08100000
hi = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x08140000

img = open(IMG, "rb").read()
NI = len(img)


def s_at(va, maxlen=64):
    f = va - VA0
    if not (0 <= f < NI):
        return None
    e = img.find(b"\x00", f)
    if e < 0 or e - f > maxlen or e == f:
        return None
    s = img[f:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


regs = []
with open(os.path.join(dump, "regions.txt"), encoding="utf-8", errors="replace") as f:
    for ln in f:
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split()
        if len(p) >= 3:
            regs.append((int(p[0], 16), int(p[1], 16), p[2]))

best = {}
for base, size, fn in regs:
    if base + size <= lo or base >= hi:
        continue
    data = open(os.path.join(dump, "mem", fn), "rb").read()
    s = max(lo, base)
    e = min(hi, base + size)
    for off in range(s - base, e - base - 16, 1):
        nm_ptr = struct.unpack_from("<I", data, off)[0]
        if not (VA0 <= nm_ptr < VA0 + NI):
            continue
        nm = s_at(nm_ptr)
        if not nm or not (nm[0].isalpha() or nm[0].isdigit()):
            continue
        fl = struct.unpack_from("<I", data, off + 4)[0]
        ty = struct.unpack_from("<I", data, off + 8)[0]
        va = struct.unpack_from("<I", data, off + 12)[0]
        if fl > 0x000F0000 or ty > 0xFF:
            continue
        addr = base + off
        rec = (addr, nm, fl, ty, va)
        if nm not in best or addr < best[nm][0]:
            best[nm] = rec

rows = sorted(best.values(), key=lambda r: (r[1]))
with open(out, "w", encoding="utf-8") as f:
    f.write("# 活 dvar 表  来源=%s  区间=[%08X,%08X)  记录=%d\n" % (dump, lo, hi, len(rows)))
    f.write("# %-10s %-34s %-9s %-4s %s\n" % ("dvar_t@", "name", "flags", "type", "value"))
    for addr, nm, fl, ty, va in rows:
        extra = ""
        if ty == 1:
            extra = " f32=%r" % struct.unpack("<f", struct.pack("<I", va))[0]
        elif ty == 7:
            st = s_at(va)
            if st:
                extra = " str=%r" % st
        f.write("%08X   %-34s %08X  %4d %08X%s\n" % (addr, nm, fl, ty, va, extra))

print("活 dvar 表: %d 条 -> %s" % (len(rows), out))
for addr, nm, fl, ty, va in rows[:40]:
    print("  %-34s flags=%08X type=%-3d value=%08X" % (nm, fl, ty, va))
