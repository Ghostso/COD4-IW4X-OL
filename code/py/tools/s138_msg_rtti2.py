#!/usr/bin/env python3
"""s138_msg_rtti2: 用"反序列化器函数指针出现在哪个 vtable 里"来给每种 type 定类名。
   这比追 'mov [reg],imm32' 更可靠, 因为 vtable 本身就是类的 RTTI 载体。
"""
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


def rtti_at_vtable(vt):
    f = vt - VA
    if not (0 <= f - 4 < N):
        return None
    col = struct.unpack_from("<I", d, f - 4)[0]
    cf = col - VA
    if not (0 <= cf < N - 4):
        return None
    ti = struct.unpack_from("<I", d, cf)[0]
    return cstr(ti + 8)


# 0xDC0000..0xDD0000 每 4 字节当作潜在 vtable 槽
LO, HI = 0xDC0000, 0xDD0000


def find_in_vtables(target):
    """返回所有 'vtable 槽 == target' 的 (vtable基址, 槽索引)"""
    hits = []
    pat = struct.pack("<I", target)
    idx = LO - VA
    while True:
        p = d.find(pat, idx, HI - VA)
        if p < 0:
            break
        idx = p + 1
        if p % 4:
            continue
        va = VA + p
        # 向右找 vtable 基址: COL 是合法指针且在镜像内
        for back in range(0, 0x40, 4):
            cand = va - back
            name = rtti_at_vtable(cand)
            if name:
                hits.append((cand, back // 4, name))
                break
    return hits


DESERS = {
    0x02: 0x625940, 0x03: None, 0x04: 0x625DB0, 0x05: 0x626B30,
    0x06: 0x627230, 0x07: 0x627B40, 0x08: 0x627CE0, 0x09: 0x627B40,
    0x0A: 0x626130, 0x0C: 0x625F50, 0x0E: 0x627E00, 0x0F: 0x627EE0,
    0x10: 0x629090, 0x11: 0x625DB0, 0x12: 0x628B90, 0x13: 0x6280B0,
    0x14: 0x628260, 0x15: 0x625DB0, 0x16: 0x6284E0, 0x17: 0x628610,
    0x18: 0x6268A0, 0x1A: 0x625DB0, 0x1B: 0x6283C0, 0x1C: 0x626730,
    0x1D: 0x6263C0, 0x1E: 0x625DB0, 0x1F: 0x627CE0, 0x20: 0x629020,
    0x21: 0x629090, 0x22: 0x6291B0, 0x23: 0x625DB0, 0x24: 0x625DB0,
    0x25: 0x6269E0, 0x26: 0x628740, 0x27: 0x629090, 0x2B: 0x627C30,
    0x2C: 0x625AB0, 0x2D: 0x629090, 0x2E: 0x629090,
}

cache = {}
print("| type | 反序列化器 | 所在 vtable | 槽 | C++ 类名 |")
print("|------|-----------|-------------|-----|----------|")
for t in sorted(DESERS):
    de = DESERS[t]
    if de is None:
        print("| 0x%02X | (无) | - | - | - |" % t)
        continue
    if de not in cache:
        cache[de] = find_in_vtables(de)
    hits = cache[de]
    if not hits:
        print("| 0x%02X | 0x%08X | (无 vtable 引用) | - | ? |" % (t, de))
        continue
    for (vt, slot, name) in hits:
        print("| 0x%02X | 0x%08X | 0x%08X | %2d | %s |" % (
            t, de, vt, slot, name.replace(".?AV", "").replace("@@", "")))
