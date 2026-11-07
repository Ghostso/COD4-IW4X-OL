#!/usr/bin/env python3
"""s138_callfields: 找 call dword [reg+0x25b8/0x25bc/0x25c0/0x25c4] 的调用点."""
import struct, sys, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a

# FF /2 (call r/m32) with modrm mod=10 (disp32): FF 90 | FF 91 | FF 92 ...
for field in (0x25b8, 0x25bc, 0x25c0, 0x25c4):
    print("=== call dword [r+0x%X] ===" % field)
    disp = struct.pack("<I", field)
    # search for pattern: ff (90..97) <disp32>
    n = 0
    for i in range(TL - VA, TH - VA - 6):
        if d[i] == 0xFF and d[i+1] in (0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97):
            if d[i+2:i+6] == disp:
                print("  @VA 0x%08X modrm=0x%02X" % (VA + i, d[i+1]))
                n += 1
    if n == 0: print("  (none)")

print("\n=== also mov/lea references to the four funcs (as imm) ===")
for fn in (0x6371F0, 0x6374E0, 0x637520, 0x633D50):
    pat = struct.pack("<I", fn)
    hits = [m.start() for m in re.finditer(re.escape(pat), d)]
    print("  0x%08X refs: %s" % (fn, [hex(h + VA) for h in hits[:12]]))
