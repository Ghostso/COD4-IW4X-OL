#!/usr/bin/env python3
"""138: 用活进程 dump 验证「房间事件分发对象」在运行时的真实身份。

原理: MSVC RTTI —— COL → type_info → name(在 ti+8)。
在 dump 里找 **指向 type_info 的指针**(COL+0x0C 或 vtable[-1]) ⇒ 反查类名。
再统计每类**实例化次数**(有多少个 vtable 指向它 / 有多少对象)。

用法: python -X utf8 tools\s138_dump_classes.py <dumpdir> [类名关键字...]
"""
import os
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IMG = r"E:\codol_re\client_image_20261027.bin"
VA0 = 0x400000
dump = sys.argv[1]
kws = sys.argv[2:] or ["dwRoom", "dwParty", "EventHandler", "CallbackHandler",
                       "InRoomEventHandler", "RoomListEventHandler",
                       "QuickMatchEventHandler", "dwRoomMatchUber"]

img = open(IMG, "rb").read()
NI = len(img)


def s_at(va, maxlen=160):
    f = va - VA0
    if not (0 <= f < NI):
        return None
    e = img.find(b"\x00", f)
    if e < 0 or e - f > maxlen or e == f:
        return None
    s = img[f:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


# 1) 静态侧: 枚举所有 type_info 及其名字 (名字在 ti+8)
ti_name = {}
for m in re.finditer(rb"\.\?A[VU][A-Za-z0-9_@?$<>,\-]{2,120}@@", img):
    name_va = VA0 + m.start()
    ti = name_va - 8           # type_info 结构: +0x00 vfptr, +0x04 ?, +0x08 name
    ti_name[ti] = m.group().decode("latin1")
print("静态 type_info 数 =", len(ti_name))

# 只保留关键字的 type_info → 4字节模式
want = {}
for ti, nm in ti_name.items():
    if any(k in nm for k in kws):
        want[struct.pack("<I", ti)] = nm
print("关键字命中的 type_info =", len(want))
for pat, nm in sorted(want.items(), key=lambda kv: kv[1])[:50]:
    print("   ", nm)

# 2) 在 dump 里数引用次数 (每个 type_info 被几个 vtable/COL 引用)
regs = []
with open(os.path.join(dump, "regions.txt"), encoding="utf-8", errors="replace") as f:
    for ln in f:
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split()
        if len(p) >= 3:
            regs.append((int(p[0], 16), int(p[1], 16), p[2]))

cnt = {nm: 0 for nm in want.values()}
where = {}
for base, size, fn in regs:
    try:
        data = open(os.path.join(dump, "mem", fn), "rb").read()
    except OSError:
        continue
    for pat, nm in want.items():
        pos = 0
        while True:
            i = data.find(pat, pos)
            if i < 0:
                break
            pos = i + 1
            cnt[nm] += 1
            where.setdefault(nm, []).append(base + i)

print("\n=== 运行时 type_info 引用次数（= 该类的 vtable/COL 实例数）===")
for nm, c in sorted(cnt.items(), key=lambda kv: -kv[1]):
    if c:
        short = nm
        for sep in ("AV", "AU"):
            if sep in short:
                short = short.split(sep, 1)[1]
                break
        short = short.split("@@")[0]
        print("  %-52s x%-4d  e.g. 0x%08X" % (short, c, where[nm][0]))
print("\n(计数为 0 的类 = 运行时**没有**该 type_info 引用 ⇒ 可能对象未创建)")
zero = [nm for nm, c in cnt.items() if c == 0]
for nm in sorted(zero)[:30]:
    print("   0:", nm)
