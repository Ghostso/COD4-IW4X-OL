#!/usr/bin/env python3
"""138 · 离线挖 dump（A4）：数字命名 dvar 的**运行期值**。

原理: dvar_t = {name_ptr@+0x00, flags@+0x04, type@+0x08, value@+0x0C}。
  1) 在静态镜像里定位每个 dvar 名字串(如 "3265")的 VA
  2) 在活进程 dump 的区域文件里搜"指向该 VA 的 4 字节小端指针"
  3) 命中处即 dvar_t 的 name 字段 => 读 +0x04/+0x08/+0x0C

用法: python -X utf8 tools\dyn138_mine_dvars.py <dumpdir> [name...]
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IMG = r"E:\codol_re\client_image_20261027.bin"
VA0 = 0x400000
NAMES = sys.argv[2:] or ["2486", "3265", "2489", "2574", "2500", "2810", "2654",
                         "3291", "3292", "1760", "1146", "1118", "16384", "516",
                         "g_gametype", "g_difficulty", "mapname", "sv_running"]

dump = sys.argv[1]
img = open(IMG, "rb").read()
NI = len(img)

# 1) 名字串候选 VA
name_vas = {}
for n in NAMES:
    pat = n.encode() + b"\x00"
    vas = []
    pos = 0
    while True:
        i = img.find(pat, pos)
        if i < 0:
            break
        # 只收"看起来像独立名字"的: 前一个字节不是标识符字符
        if i == 0 or not (chr(img[i - 1]).isalnum() or img[i - 1] in b"_.$"):
            vas.append(VA0 + i)
        pos = i + 1
    name_vas[n] = vas
print("静态镜像里名字串候选数:", {k: len(v) for k, v in name_vas.items()})

# 2) 区域清单
regs = []
with open(os.path.join(dump, "regions.txt"), encoding="utf-8", errors="replace") as f:
    for ln in f:
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split()
        if len(p) >= 3:
            regs.append((int(p[0], 16), int(p[1], 16), p[2]))
print("dump 区域 %d 个" % len(regs))

# 预生成所有候选 VA 的 4 字节模式
want = {}
for n, vas in name_vas.items():
    for v in vas:
        want[struct.pack("<I", v)] = (n, v)

hits = {}     # (name) -> list of (dvar_addr, value, flags, type)
for base, size, fn in regs:
    path = os.path.join(dump, "mem", fn)
    try:
        data = open(path, "rb").read()
    except OSError:
        continue
    for pat, (n, v) in want.items():
        pos = 0
        while True:
            i = data.find(pat, pos)
            if i < 0:
                break
            pos = i + 1
            addr = base + i
            # 候选 dvar_t 从 i 开始
            def u32(off):
                j = i + off
                return struct.unpack_from("<I", data, j)[0] if j + 4 <= len(data) else None
            hits.setdefault(n, []).append((addr, u32(0x0C), u32(0x04), u32(0x08)))

print()
for n in NAMES:
    hs = hits.get(n, [])
    if not hs:
        print("%-12s : 无指针命中" % n)
        continue
    print("%-12s : %d 处" % (n, len(hs)))
    for addr, val, flags, typ in hs[:6]:
        fv = ("%08X" % flags) if flags is not None else "?"
        tv = ("%08X" % typ) if typ is not None else "?"
        vv = ("%08X" % val) if val is not None else "?"
        iv = ""
        if val is not None and val < 1 << 31:
            iv = " (u32=%d)" % val
        print("      dvar_t@%08X  flags=%s type=%s value=%s%s" % (addr, fv, tv, vv, iv))
