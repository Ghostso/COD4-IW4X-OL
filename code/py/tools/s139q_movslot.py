# -*- coding: utf-8 -*-
"""139q: 在各 handler 里找 mov edx/eax,[reg+disp32] + call edx/eax 的组合（vtable 派发）。"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = open(r"E:\codol_re\client_image_20261027.bin", "rb").read()
VA = 0x400000

TARGETS = {
    0xB7B210: "type6  ",
    0xB7B300: "type7  ",
    0xB7B4B0: "type9  ",
    0xB7B650: "type31 ",
    0xB7B820: "type32 ",
}
for fn, tag in TARGETS.items():
    o = fn - VA
    print(f"\n=== {tag} 0x{fn:08X} ===")
    for k in range(0x500):
        if d[o + k] != 0x8B:      # mov
            continue
        m = d[o + k + 1]
        reg = (m >> 3) & 7
        mod, rm = m >> 6, m & 7
        if mod == 2 and rm != 4:
            disp = struct.unpack_from("<I", d, o + k + 2)[0]
            if disp < 0x200:
                print(f"  0x{fn+k:08X}  mov r{reg},[r{rm}+0x{disp:03X}]")
