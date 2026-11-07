#!/usr/bin/env python3
"""0x2411c1 / 0x24125d 附近的指针表布局.
把该区域按 8 字节 {ptr,ptr} 或 4 字节 ptr 扫描, 解析指向的串.
判定: 是不是一张 {name_ptr, fmt_ptr} 事件注册表.
"""
import struct, re
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

def cstr(off, maxlen=300):
    if not (0 <= off < N): return b"<OOB>"
    e = d.find(b"\x00", off)
    if e < 0 or e - off > maxlen: e = off + maxlen
    return d[off:e]

def rd(m, o, n):
    b = d[o:o+n]
    if len(b) != n: return None
    return int.from_bytes(b, "little")

for center in (0x2411c1, 0x24125d):
    print("=" * 70)
    print("中心 file 0x%X (VA 0x%X)" % (center, center + VA))
    # 8 字节一行, 覆盖 ±0x80
    start = (center - 0x80) & ~7
    cur = start
    while cur < center + 0x90:
        b = d[cur:cur+8]
        print("  0x%06X : %s" % (cur, " ".join("%02x" % x for x in b)))
        cur += 8
    print()
    # 解释附近 u32 值: 若落在 VA 区间且指向可打印串
    print("  -- 附近 u32 解释 --")
    for o in range((center - 0x40) & ~3, center + 0x48, 4):
        v = rd(None, o, 4)
        tag = ""
        if VA <= v < VA + N:
            s = cstr(v - VA, 60)
            if s and all(32 <= c < 127 or c in (9,10) for c in s):
                tag = "-> %r" % s[:60]
        print("    0x%06X: 0x%08X %s" % (o, v, tag))
