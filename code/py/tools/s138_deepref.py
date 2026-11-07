#!/usr/bin/env python3
"""138: 深搜某函数 VA 的一切可能引用（含 call/jmp [表]、lea、push、位移寻址、SEH 表）。"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

tgt = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x7E7C90
le32 = struct.pack("<I", tgt)
be32 = struct.pack(">I", tgt)
le16 = struct.pack("<H", tgt & 0xFFFF)

print("目标 0x%08X" % tgt)
for name, pat in (("LE32", le32), ("BE32", be32), ("LE16(低16)", le16)):
    pos, n = 0, 0
    print("\n-- %s --" % name)
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        n += 1
        va = VA + i
        ctx = " ".join("%02x" % c for c in d[max(0, i - 8):i + 10])
        print("   0x%08X  %s" % (va, ctx))
        if n > 40:
            print("   ...(截断)")
            break
    if n == 0:
        print("   0 处")

# 也检查 rdata 里是否有相对偏移表（.text 内 lea reg,[ebx+imm] 指向数据段表）
print("\n-- 检查 0x7E7C 附近被当 u32 的低位半字 --")
lo = tgt & 0xFFFF
cnt = 0
pos = 0
while cnt < 10:
    i = d.find(struct.pack("<H", lo), pos)
    if i < 0:
        break
    pos = i + 1
    # 只关心高 16 位也像 0x0000 或邻接
    hi = struct.unpack_from("<H", d, i + 2)[0] if i + 4 <= N else 0
    if hi == 0x0000:
        cnt += 1
        print("   0x%08X  低16=0x%04X 高16=0x%04X" % (VA + i, lo, hi))
