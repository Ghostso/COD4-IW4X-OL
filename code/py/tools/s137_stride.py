#!/usr/bin/env python3
"""137: scan for imul reg,reg,<stride> and add reg,<stride> with context."""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

stride = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x1D0
sp = struct.pack("<I", stride)

print("== imul r32,r/m32,0x%X (69 /r imm32) ==" % stride)
hits = []
for i in range(N - 6):
    if d[i] == 0x69 and d[i + 2:i + 6] == sp:
        hits.append(VA + i)
print("count =", len(hits))
for h in hits[:80]:
    print("   0x%08X  %s" % (h, d[h - VA - 3:h - VA + 8].hex(" ")))

print()
print("== add r32,0x%X (81 /0 imm32: 81 Cx ..) ==" % stride)
hits2 = []
for i in range(N - 6):
    if d[i] == 0x81 and d[i + 1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC6, 0xC7,
                                     0xE8, 0xE9, 0xEA, 0xEB, 0xEE, 0xEF) \
            and d[i + 2:i + 6] == sp:
        hits2.append(VA + i)
print("count =", len(hits2))
for h in hits2[:80]:
    print("   0x%08X  %s" % (h, d[h - VA - 3:h - VA + 8].hex(" ")))
