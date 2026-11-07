#!/usr/bin/env python3
"""138: 判断 0x6371F0 是否为虚函数（出现在某个 vtable 里）。
若在 vtable：反查 vtable→COL→类名，得出「房间消息接收回调属于哪个类」。
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def rd(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f < N - 4 else None


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def cls_of_vtable_slot(slot_va):
    """slot_va 指向函数；若它是某 vtable 的槽，返回 (vtable_va, index, 类名)。"""
    # 找所有指向 slot_va 的 dword（可能是 vtable 槽）
    pat = struct.pack("<I", slot_va)
    res = []
    pos = 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        hit = VA + i
        # 向前回溯到 vtable 起点：vftable[-1] 应是合法 COL
        for back in range(4, 0x300, 4):
            cand = hit - back
            col = rd(cand - 4)
            if not col or not (VA <= col < VA + N):
                continue
            ti = rd(col + 0x0C)
            if not ti or not (VA <= ti < VA + N):
                continue
            nm = cstr(ti + 8)
            if nm and nm.startswith(".?"):
                res.append((cand, back // 4, nm, hit))
                break
    # 去重
    out = {}
    for cand, idx, nm, hit in res:
        out[(cand, nm)] = idx
    return out


for a in sys.argv[1:]:
    tgt = int(a, 0)
    print("=" * 70)
    print("0x%08X 是否在某 vtable 中：" % tgt)
    r = cls_of_vtable_slot(tgt)
    if not r:
        print("   未找到（可能是普通函数 / SEH 处理器 / 回调被运行时填充）")
    for (vt, nm), idx in sorted(r.items()):
        print("   vtable 0x%08X  槽[%d]  类=%s" % (vt, idx, nm))
