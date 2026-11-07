#!/usr/bin/env python3
"""s138_rectable: 扫描 [u32 svc][u32 task][u32 code ptr] 记录表 (svc 6/11/8/21等)."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a
SVC = {3,4,6,8,9,10,11,12,13,14,15,18,19,21,28,29,68,71,80,93,102}

def u32(o):
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

rows = []
for off in range(0, N - 16, 4):
    svc = u32(off); task = u32(off + 4); fn = u32(off + 8)
    if svc in SVC and 0 <= task <= 200 and fn and TL <= fn < TH:
        rows.append((off, svc, task, fn, u32(off+12)))

# group by contiguity
print("=== 命中 %d ===" % len(rows))
# print only runs of >=2 consecutive (step 16) with same-ish pattern
prev = None
run = []
def flush(run):
    if len(run) >= 2:
        for off, svc, task, fn, x in run:
            print("  0x%08X  svc=%-3d task=%-3d fn=0x%08X x=%s" % (off+VA, svc, task, fn, x))
        print("  ---")
for r in rows:
    if prev is not None and r[0] == prev[0] + 16:
        run.append(r)
    else:
        flush(run); run = [r]
    prev = r
flush(run)
