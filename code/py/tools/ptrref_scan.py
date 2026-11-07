#!/usr/bin/env python3
"""扫某 VA 的绝对引用: 立即数出现位置 / 表格插槽位置 / 相对位移位置."""
import re, struct, sys
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
def out(s): sys.stdout.write(s.encode("ascii","replace").decode("ascii")+"\n")
def cstr(f):
    e = d.find(b"\x00", f)
    return d[f:e] if e > f else b''
ARGS = [x for x in sys.argv[1:] if x != "--calls"]

for a in ARGS:
    v = int(a, 0)
    out("="*70); out("### 目标 VA 0x%06X" % v)
    pat = struct.pack("<I", v)
    hits = [m.start() for m in re.finditer(re.escape(pat), d)]
    out("  完整 4 字节立即数出现 %d 次: %s" % (len(hits), " ".join("0x%06X" % h for h in hits[:20])))
    # 表格插槽: 目标落在 "[u32][u32]" 对里且前一 dword < 0x100
    slots = [h for h in hits if h >= 4 and struct.unpack_from("<I", d, h-4)[0] < 0x1000]
    out("  疑似[count][ptr] 表项: %s" % (" ".join("0x%06X" % h for h in slots[:12]) if slots else "无"))
    # 相对位移 (表格里存 ptr - table_base, table_base 未知 → 直接找任何 4 字节即目标-table_base 不现实)
    out("")


# ---- rel32 调用点扫描（正确形式；本卷踩过 E8+绝对地址 的坑）----
def callsites_va(target, a=0, b=None):
    b = b if b is not None else N - 5
    res = []
    i = a
    while True:
        j = d.find(b"\xe8", i)
        if j < 0 or j + 5 > b: break
        if (j + 5 + VA) + struct.unpack_from("<i", d, j + 1)[0] == target:
            res.append(j)
        i = j + 1
    return res


if "--calls" in sys.argv:
    out("=" * 70)
    out("### rel32 调用点扫描")
    for a in ARGS:
        t = int(a, 0)
        cs = callsites_va(t)
        out("  target 0x%06X : %d 处 -> %s" % (t, len(cs),
            " ".join("0x%06X" % c for c in cs[:30]) if cs else "NONE"))
