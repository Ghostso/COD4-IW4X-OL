# -*- coding: utf-8 -*-
"""139p: 找 type6/7/8/9/31/32 handler 里的 call [reg+disp]，确定各自走哪个 vtable slot。"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()
VA = 0x400000

TARGETS = {
    0xB7B210: "type6  0xB7B210",
    0xB7B300: "type7  0xB7B300",
    0xB7B4B0: "type9  0xB7B4B0",
    0xB7B650: "type31 0xB7B650",
    0xB7B820: "type32 0xB7B820",
}
for fn, tag in TARGETS.items():
    print(f"\n=== {tag} ===")
    o = fn - VA
    # 扫 0x400 字节
    for k in range(0x400 - 2):
        if d[o + k] != 0xFF:
            continue
        m = d[o + k + 1]
        if (m & 0x38) != 0x10:   # call
            continue
        mod = m >> 6
        rm = m & 7
        if mod == 2 and rm != 4:
            disp = struct.unpack_from("<I", d, o + k + 2)[0]
            if disp < 0x200:
                print(f"  0x{fn+k:08X}  call [reg+0x{disp:03X}]")
