#!/usr/bin/env python3
"""s138_triples: 扫 {u32 svc, u32 task} 后接 <=24 字节内有代码指针 的记录."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a

def is_code(v): return TL <= v < TH

print("=== (svc=6 or any, task=5) 记录 且邻近有代码指针 ===")
seen = set()
for off in range(0, N - 32, 4):
    svc, task = struct.unpack_from("<II", d, off)
    if svc not in (3,4,6,8,9,10,11,12,21,28,29,68,71,80,93,102): continue
    if not (1 <= task <= 64): continue
    if (svc, task) not in ((6,5),(6,14),(6,18),(6,8),(6,2)): continue
    nxt = struct.unpack_from("<IIII", d, off + 8)
    codes = [x for x in nxt if is_code(x)]
    if codes:
        key = (svc, task, off)
        if key in seen: continue
        seen.add(key)
        print("  file0x%07X VA0x%08X %d/%d next4=%s %s" % (
            off, off + VA, svc, task, [hex(x) for x in nxt],
            ["CODE" if is_code(x) else "" for x in nxt]))

print("\n=== 反向: 代码指针后接 svc/task ===")
for off in range(0, N - 32, 4):
    p = struct.unpack_from("<I", d, off)[0]
    if not is_code(p): continue
    svc, task = struct.unpack_from("<II", d, off + 4)
    if svc in (3,4,6,8,9,10,11,12,21,28,29,68,71,80,93,102) and 1 <= task <= 64:
        if svc == 6:
            print("  file0x%07X VA0x%08X fn=0x%08X svc=%d task=%d" % (
                off, off + VA, p, svc, task))
