# -*- coding: utf-8 -*-
"""139u/140: 确认 0xB83744 主表恰 75 项、0xB83870 起第二表；并打印两表全展开。"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()
VA = 0x400000

T1, T2 = 0xB83744, 0xB83870
print(f"0xB83870 - 0xB83744 = 0x{T2-T1:X} = {(T2-T1)//4} 项")
print()
print("=== 主表 (类型号 = 索引+1, 1..75) ===")
for i in range((T2 - T1) // 4):
    v = struct.unpack_from("<I", d, T1 - VA + i * 4)[0]
    print(f"  type {i+1:2d} (0x{i+1:02X})  -> 0x{v:08X}")
print()
print("=== 第二表 (类型号 = 索引+1002) ===")
for i in range(9):
    v = struct.unpack_from("<I", d, T2 - VA + i * 4)[0]
    print(f"  type {1002+i}  -> 0x{v:08X}")
print()
print("=== 特殊 ===")
print("  type 1001 -> 0xB7CCE0   (0xB82D3C je 0xB83547)")
print("  其它      -> 0xB836CC   (default)")
