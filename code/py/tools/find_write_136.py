#!/usr/bin/env python3
"""136 卷工具 B: 直接搜 0xC77BB98 的**写点**(决定它的类/vtable => GFx 接口表)."""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
ABS = struct.pack("<I", 0x0C77BB98)

PATS = [
    ("a3 (mov [abs],eax)", b"\xa3" + ABS),
    ("c7 05 (mov dword [abs],imm32)", b"\xc7\x05" + ABS),
    ("89 05 (mov [abs],eax)", b"\x89\x05" + ABS),
    ("89 0d (mov [abs],ecx)", b"\x89\x0d" + ABS),
    ("89 15 (mov [abs],edx)", b"\x89\x15" + ABS),
    ("89 1d (mov [abs],ebx)", b"\x89\x1d" + ABS),
    ("89 35 (mov [abs],esi)", b"\x89\x35" + ABS),
    ("89 3d (mov [abs],edi)", b"\x89\x3d" + ABS),
    ("c7 05 w/ -1 ...", b"\xc7\x05" + ABS),
]

for name, pat in PATS:
    pos = 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        tail = d[i:i + 10].hex()
        print("0x%08X  %-34s  bytes: %s" % (VA + i, name, tail))
print("--- 若上面为空, 说明该全局只被读, 写点在别处(如 mov [reg+disp]) ---")
