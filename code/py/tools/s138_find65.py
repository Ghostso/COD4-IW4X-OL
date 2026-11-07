#!/usr/bin/env python3
"""s138_find65: 找 'push 6' 与 'push 5' 相邻的调用簇, 及 push 0x14 邻近."""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TEXT_LO, TEXT_HI = 0x401000 - VA, 0x8a689a  # file offsets

md = Cs(CS_ARCH_X86, CS_MODE_32)

# 1) find "6a 06" (push 6) and "6a 05" (push 5) byte sequences, near each other
print("=== 相邻 push imm8 6 与 5 的簇 (window <= 64 bytes) ===")
pushes = []
for i in range(TEXT_LO, min(TEXT_HI, N) - 2):
    if d[i] == 0x6A:
        v = d[i+1]
        if v in (5, 6, 0x14, 0x0e, 0x12):
            pushes.append((i, v))
# find clusters containing both 5 and 6
found = 0
for idx in range(len(pushes) - 1):
    a = pushes[idx]
    for jdx in range(idx + 1, len(pushes)):
        b = pushes[jdx]
        if b[0] - a[0] > 96:
            break
        vals = {a[1], b[1]}
        if 5 in vals and 6 in vals:
            print("  @VA 0x%08X push%d .. @VA 0x%08X push%d" %
                  (VA + a[0], a[1], VA + b[0], b[1]))
            found += 1
            if found > 40:
                break
    if found > 40:
        break
print("  total clusters:", found)
