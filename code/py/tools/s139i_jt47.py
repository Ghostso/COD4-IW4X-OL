# -*- coding: utf-8 -*-
"""139i: 找 0x636F3C 的所有引用；确认它是否 jmp [eax*4+0x636F3C] 以及 eax 是否有 dec。"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
IMG = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(IMG, "rb").read()

for t in (0x636F3C, 0x82E1458):
    p = struct.pack("<I", t)
    i, hits = 0, []
    while True:
        j = d.find(p, i)
        if j < 0:
            break
        hits.append(j + VA)
        i = j + 1
    print(f"0x{t:08X} dword refs ({len(hits)}): {[hex(x) for x in hits]}")

# 也找 FF 24 85 <disp32> 形态（jmp [eax*4+disp]）
print("\n=== jmp [eax*4+disp32] 形态 ===")
for i in range(len(d) - 7):
    if d[i] == 0xFF and d[i+1] == 0x24 and d[i+2] == 0x85:
        disp = struct.unpack_from("<I", d, i + 3)[0]
        if 0x600000 < disp < 0x900000:
            print(f"  0x{i+VA:08X}  jmp [eax*4+0x{disp:08X}]")
