#!/usr/bin/env python3
"""s138_svc6: 找所有 (u32==6, u32==5) 相邻的位置, 打印上下文 dword 与字符串."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a

def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

def cstr(va, ml=60):
    o = va - VA
    if not (0 <= o < N - 1): return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2: return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None

print("=== 相邻 u32 6,5 (对齐 4) ===")
pat = struct.pack("<II", 6, 5)
i = 0
cnt = 0
while True:
    j = d.find(pat, i)
    if j < 0: break
    i = j + 1
    if j % 4 != 0: continue
    va = VA + j
    # print neighbors
    neigh = [u32(va + 4*k) for k in range(-3, 5)]
    notes = []
    for k, v in zip(range(-3, 5), neigh):
        if v is None: continue
        if TL <= v < TH: notes.append(("d%d" % k, hex(v), "CODE"))
        else:
            s = cstr(v) if v else None
            if s: notes.append(("d%d" % k, hex(v), "STR %r" % s))
            elif v < 0x1000: notes.append(("d%d" % k, v, ""))
    print("  @VA 0x%08X  %s" % (va, notes))
    cnt += 1
    if cnt > 60: break
print("total", cnt)
