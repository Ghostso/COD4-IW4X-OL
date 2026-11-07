#!/usr/bin/env python3
"""扫 AS_* 类族登记表: 12 字节记录 [0x693DD0][handler][typeinfo], typeinfo 内嵌 .?AVAS_*@@ 名.

131 卷工具. 输出 {类名, handler VA, typeinfo VA} 全表.
"""
import re, struct, sys

E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read()
N = len(d)
VA = 0x400000


def out(s):
    sys.stdout.write(s + "\n")


def cstr(va):
    f = va - VA
    if not (0 <= f < N):
        return b"<oob>"
    e = d.find(b"\x00", f)
    return d[f:e] if 0 <= e - f < 300 else b"<bin>"


# 1) 所有 .?AVAS_ 名字串
names = {}
for m in re.finditer(rb"\.\?A[VU][A-Za-z0-9_@?$<>,\-]*@@", d):
    names[VA + m.start()] = m.group().decode("latin1")
out("AS_* 名字串 %d 条" % len(names))

# 2) typeinfo -> 名字. typeinfo 布局: +0x0C ptr 指向 {ptr,0,name@+8}
tinfo = {}   # typeinfo VA -> (name_ptr VA, name)
for tn, _ in list(names.items()):
    # 名字串的宿主结构 = 名字串地址 - 8
    host = tn - 8
    # 全镜像里谁把 host 当指针存了? 反查: 找 "typeinfo+0x0C == host"
    # 直接扫 .data 里 12 字节记录更省事, 见下
    pass

# 3) 扫 12 字节记录
recs = []
for m in re.finditer(re.escape(struct.pack("<I", 0x00693DD0)), d):
    f = m.start()
    if f + 12 > N:
        continue
    _, fn, ti = struct.unpack_from("<III", d, f)
    if not (VA <= fn < VA + N):
        continue
    if not (VA <= ti < VA + N):
        continue
    t = ti - VA
    try:
        a, b, c = struct.unpack_from("<III", d, t)
        p = struct.unpack_from("<I", d, t + 0x0C)[0]
        _p2 = struct.unpack_from("<I", d, t + 0x10)[0]
        _n = struct.unpack_from("<I", d, t + 0x1C)[0]
    except struct.error:
        continue
    if not (VA <= p < VA + N):
        continue
    nm = cstr(p + 8)
    if not (nm.startswith(b".?A")):
        continue
    recs.append((VA + f, fn, ti, nm.decode("latin1")))

out("12 字节记录命中 %d 条" % len(recs))
out("")
out("%-34s %-10s %-10s %s" % ("类名", "记录", "handler", "typeinfo"))
for rec_va, fn, ti, nm in recs:
    out("%-34s 0x%08X 0x%08X 0x%08X" % (nm, rec_va, fn, ti))

# 4) 名字串有但记录里没有的
covered = {nm for _, _, _, nm in recs}
out("")
out("未被记录覆盖的 AS_ 名: %s" % ("无" if set(names.values()) <= covered
                                else ", ".join(sorted(set(names.values()) - covered))))
