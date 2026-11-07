#!/usr/bin/env python3
"""136 卷工具 F: 统计 `mov dword ptr [reg+0x0C], imm32` (C7 4? 0C imm32) 的 imm 直方图
—— 若 135 的 `(x & 0x8F)==0x0A` 是"GFx::Value 类型字段", 那么写入该字段的值应当聚在小整数上."""
import re
import struct
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()

hist = Counter()
samples = {}
SHOW = [0x0A, 6, 1, 5, 9, 8, 0, 2, 3, 4, 7]

for m in re.finditer(rb"\xc7", d):
    i = m.start()
    if i + 7 > len(d):
        continue
    if d[i + 1] & 0xC0 != 0x40:        # mod=01
        continue
    if (d[i + 1] >> 3) & 7 == 0:       # reg=000 -> mov r/m32, imm32  (但要 0x0C disp)
        pass
    if d[i + 2] != 0x0C:               # disp8 = 0x0C
        continue
    imm = struct.unpack_from("<I", d, i + 3)[0]
    if imm > 0x1000:
        continue
    hist[imm] += 1
    if imm in SHOW and imm not in samples:
        samples[imm] = VA + i

print("[reg+0xC] = imm32 直方图 (imm<=0x1000), 共 %d 处" % sum(hist.values()))
for v, c in hist.most_common(24):
    print("   imm=0x%04X (%d)  x%d   e.g. 0x%08X" % (v, v, c, samples.get(v, 0)))
