#!/usr/bin/env python3
"""s138_channels: 枚举 stride 0x25d0 的 'channel' 描述符, 打印 key 与 4 个回调."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a

def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

BASE = 0xE374650
S = 0x25D0
END = 0xE379200
print("=== channel descriptors (base..0xE379200) ===")
va = BASE
while va < END:
    b0 = d[va - VA]; b1 = d[va + 1 - VA]
    hi = u32(va + 0x10); lo = u32(va + 0x14)
    fns = [u32(va + 0x25b8 + 4 * k) for k in range(4)]
    hascode = any(f and TL <= f < TH for f in fns)
    if b0 != 0 or hascode:
        print("  0x%08X flags=%02x%02x key=%08X%08X fns=%s" % (
            va, b0, b1, hi or 0, lo or 0, [hex(f) if f else "0" for f in fns]))
    va += S
