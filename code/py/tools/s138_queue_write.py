#!/usr/bin/env python3
"""138: 找 dwLobbyImp 的待处理消息队列 [obj+0x4F0] 的写入点（= 收包入队处）。"""
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

# mov [reg+0x4F0], r32   => 89 8?/9?/a?.. with disp32 0x4F0
# 编码: 89 /r  reg 字段; modrm mod=10 (disp32)
print("=== mov [reg+0x4F0], r32 (89 modrm disp32=0x4F0) ===")
n = 0
for m in re.finditer(rb"\x89", d):
    i = m.start()
    if i + 7 > N:
        continue
    modrm = d[i + 1]
    if modrm & 0xC7 != 0x80:      # mod=10 (disp32), rm=000 (eax base pattern ignored)
        continue
    if struct.unpack_from("<I", d, i + 2)[0] != 0x4F0:
        continue
    n += 1
    print("   0x%08X  %s" % (VA + i, d[i:i + 8].hex()))

print("共 %d" % n)

print("\n=== mov [reg+0x4F0], r32 全 modrm 形态 ===")
n2 = 0
for i in range(len(d) - 7):
    if d[i] != 0x89:
        continue
    modrm = d[i + 1]
    if (modrm >> 6) != 2:          # mod=10
        continue
    if struct.unpack_from("<I", d, i + 2)[0] != 0x4F0:
        continue
    n2 += 1
    if n2 <= 20:
        print("   0x%08X  %s" % (VA + i, d[i:i + 8].hex()))
print("共 %d" % n2)
