# -*- coding: utf-8 -*-
"""139g: (a) 0xB7A550 / 0xB7A700 的调用者与传入字符串;
(b) 0xB83744 / 0xB83870 两表按"类型号 = 索引+1"重排;
(c) 0xB82CCA 之前谁填 [ebp-0x78]。
"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
IMG = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(IMG, "rb").read()

def callers(t):
    out = []
    for i in range(len(d) - 5):
        if d[i] != 0xE8:
            continue
        if (i + 5 + struct.unpack_from("<i", d, i + 1)[0] + VA) == t:
            out.append(i + VA)
    return out

for t in (0xB7A550, 0xB7A700, 0xB7A760, 0xB7A670, 0xB80D30):
    print(f"0x{t:08X} callers: {[hex(x) for x in callers(t)]}")

print("\n=== 0xB83744 (数值表) 按 类型号=索引+1 展开 ===")
for i in range(76):
    v = struct.unpack_from("<I", d, 0xB83744 - VA + i * 4)[0]
    print(f"  类型号 {i+1:2d} (0x{i+1:02X}) -> 0x{v:08X}")

print("\n=== 0xB83870 (9 项, 类型号 1002..1010) ===")
for i in range(9):
    v = struct.unpack_from("<I", d, 0xB83870 - VA + i * 4)[0]
    print(f"  类型号 {1002+i} -> 0x{v:08X}")
