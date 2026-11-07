#!/usr/bin/env python3
"""找 '整型ID + 字符串指针' 交替的数组 (UIPage 页号 -> 页名 候选表).
判据: 连续 >=8 项, 每项 8 字节 = [u32 id (0..200)][u32 ptr -> .rdata ASCII].
也扫 [ptr][id] 顺序.
"""
import struct, sys
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read(); N = len(d)
def out(s): sys.stdout.write(s.encode("ascii","replace").decode("ascii")+"\n")
def is_ascii_ptr(v, minlen=3):
    f = v - VA
    if not (0 <= f < N-2): return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f < minlen or e - f > 120: return None
    s = d[f:e]
    if not all(32 <= c < 127 for c in s): return None
    return s.decode("latin1")

def scan(a, b, order, idmax=210, need=8):
    hits = []
    i = a
    while i + need*8 <= b:
        run = []
        j = i
        while j + 8 <= b:
            x, y = struct.unpack_from("<II", d, j)
            if order == "id_ptr":
                idv, ptr = x, y
            else:
                ptr, idv = x, y
            s = is_ascii_ptr(ptr) if idv <= idmax else None
            if s is None: break
            run.append((idv, ptr, s)); j += 8
        if len(run) >= need:
            hits.append((i, list(run)))
            i = j
        else:
            i += 4
    return hits

for order in ("id_ptr", "ptr_id"):
    out("="*74)
    out("### 顺序 %s (>=8 项)" % order)
    hits = scan(0, N, order)
    out("  命中 %d 段" % len(hits))
    for off, run in hits[:40]:
        out("  --- 段 @file0x%06X (%d 项, id 范围 %d..%d) ---" % (off, len(run), min(r[0] for r in run), max(r[0] for r in run)))
        for idv, ptr, s in run[:24]:
            out("      %-4d 0x%06X %r" % (idv, ptr-VA, s[:60]))
