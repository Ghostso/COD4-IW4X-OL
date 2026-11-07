#!/usr/bin/env python3
"""135 卷工具 D: 扫 Scaleform 接口转发器 thunk 表.

形状(17 字节):
  55              push ebp
  8b ec           mov ebp, esp
  8b 49 0c        mov ecx, [ecx+0xC]
  8b 01           mov eax, [ecx]
  8b 80 XX XX 00 00  mov eax, [eax+slot]
  5d              pop ebp
  ff e0           jmp eax
"""
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()

pat = re.compile(rb"\x55\x8b\xec\x8b\x49\x0c\x8b\x01\x8b\x80(....)\x5d\xff\xe0", re.S)
hits = []
for m in pat.finditer(d):
    slot = struct.unpack("<I", m.group(1))[0]
    hits.append((VA + m.start(), slot))

print("thunk 命中 %d 个" % len(hits))
# 按 slot 排
for va, slot in sorted(hits, key=lambda x: x[1]):
    print("  0x%08X  vt+0x%03X" % (va, slot))

# 连续块
print()
runs = []
cur = [hits[0]] if hits else []
for h in hits[1:]:
    if h[0] - cur[-1][0] <= 0x30:
        cur.append(h)
    else:
        runs.append(cur)
        cur = [h]
if cur:
    runs.append(cur)
for r in runs:
    print("块 0x%08X..0x%08X  %d 个" % (r[0][0], r[-1][0], len(r)))
