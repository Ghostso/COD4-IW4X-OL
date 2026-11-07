# -*- coding: utf-8 -*-
"""139r: 各 handler 的 disp32 读取（mod=10）全列出。"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()
VA = 0x400000

for fn, tag in ((0xB7B210, "type6"), (0xB7B300, "type7"), (0xB7B4B0, "type9"),
                (0xB7B650, "type31"), (0xB7B820, "type32")):
    o = fn - VA
    print(f"\n=== {tag} 0x{fn:08X} ===")
    k = 0
    while k < 0x300:
        if d[o + k] == 0x8B:
            m = d[o + k + 1]
            reg = (m >> 3) & 7
            mod, rm = m >> 6, m & 7
            if mod == 2 and rm != 4:
                disp = struct.unpack_from("<I", d, o + k + 2)[0]
                print(f"  0x{fn+k:08X}  mov r{reg},[r{rm}+0x{disp:03X}]")
                k += 6
                continue
        k += 1
