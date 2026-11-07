#!/usr/bin/env python3
"""s138_dwmsg_vt: 枚举所有 `.?AVdwRoomMessage*` 类的 vtable, 并列出引用它们的
   push/mov 立即数点(构造点)。
"""
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    if not s or not all(32 <= c < 127 for c in s):
        return None
    return s.decode("latin1")


# 1. 全镜像找 '.?AVdwRoomMessage' 字符串
print("=== .?AVdwRoomMessage* RTTI 名 ===")
names = []
idx = 0
needle = b".?AVdwRoomMessage"
while True:
    p = d.find(needle, idx)
    if p < 0:
        break
    idx = p + 1
    f = p
    # 该字符串起始处 = ti+8, 故 TI VA = f-8+VA
    ti_va = f - 8 + VA
    s = cstr(VA + f)
    names.append((ti_va, VA + f, s))
    print("  TI=0x%08X  name_va=0x%08X  %s" % (ti_va, VA + f, s))

# 2. 找引用这些 TI 的 COL (COL+0 == TI)
print("\n=== COL (COL+0 = TI) ===")
col_of = {}
for ti_va, _, s in names:
    pat = struct.pack("<I", ti_va)
    idx = 0
    while True:
        p = d.find(pat, idx)
        if p < 0:
            break
        idx = p + 1
        if p % 4:
            continue
        col = VA + p
        col_of.setdefault(col, []).append(s)
        print("  COL=0x%08X -> %s" % (col, s))

# 3. 找 vtable (vtable[-4] == COL)
print("\n=== vtable 与引用点 ===")
for col, snames in col_of.items():
    pat = struct.pack("<I", col)
    idx = 0
    while True:
        p = d.find(pat, idx)
        if p < 0:
            break
        idx = p + 1
        vt = VA + p + 4
        # vtable 起点 = p+4 (即 COL 后)
        print("\n  COL=0x%08X  vtable=0x%08X  %s" % (col, vt, snames[0]))
        # 前 12 个槽
        slots = []
        for k in range(12):
            slots.append(struct.unpack_from("<I", d, p + 4 + 4 * k)[0])
        print("    slots[0:12] = %s" % " ".join("0x%08X" % v for v in slots))
        # 引用点: 任何包含该 vtable 地址的 4 字节立即数
        vp = struct.pack("<I", vt)
        j = 0
        refs = []
        while True:
            q = d.find(vp, j)
            if q < 0:
                break
            j = q + 1
            if q % 4:
                continue
            refs.append(VA + q)
        print("    imm32 引用 (%d 处): %s" % (
            len(refs), " ".join("0x%08X" % r for r in refs[:20])))
