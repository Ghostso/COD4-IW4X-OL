#!/usr/bin/env python3
"""s138_tasktable: 扫 [u32 svc][u32 task][ptr name][ptr fn] 记录表 (Demonware 任务表)."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000

TEXT_LO = 0x401000
TEXT_HI = 0x401000 + 0x8a689a

def cstr(va, ml=64):
    o = va - VA
    if not (0 <= o < N - 1): return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2: return None
    s = d[o:e]
    if not all(32 <= c < 127 for c in s): return None
    return s.decode("latin1")

KNOWN_SVC = {3,4,6,8,9,10,11,12,21,28,29,68,71,80,93,102}

print("=== 扫描 [svc][task][nameptr][?] 记录 ===")
hits = []
for off in range(0, N - 16, 4):
    svc, task, p3, p4 = struct.unpack_from("<IIII", d, off)
    if svc not in KNOWN_SVC: continue
    if not (1 <= task <= 300): continue
    nm = cstr(p3)
    f3 = (TEXT_LO <= p3 < TEXT_HI)
    f4 = (TEXT_LO <= p4 < TEXT_HI)
    role = None
    if nm and f4: role = "svc,task,NAME,fn"
    elif f3 and nm is None:
        nm2 = cstr(p4)
        if nm2: role = "svc,task,fn,NAME"
    if role:
        hits.append((off, svc, task, p3, p4, nm or cstr(p4), role))

print("命中 %d 条" % len(hits))
for off, svc, task, p3, p4, nm, role in hits[:200]:
    print("  file0x%07X VA0x%08X  %d/%d  %-14r  [%s]" % (off, off+VA, svc, task, nm, role))
