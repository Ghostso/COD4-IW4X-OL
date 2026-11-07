#!/usr/bin/env python3
"""s138_desctable: 枚举 descriptor 数组 (stride 0x25d0, base 0xE374650), 找 svc=6/task=5."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a

def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

def cstr(va, ml=80):
    o = va - VA
    if not (0 <= o < N - 1): return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2: return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None

BASE = 0xE374650
STRIDE = 0x25d0
first_fn = 0xE376C08

print("=== entries ===")
for k in range(40):
    b = BASE + k * STRIDE
    fn = u32(b + 0x25b8)
    if fn is None: break
    if not (TL <= fn < TH):
        print("  [%2d] base=0x%08X fn=0x%08X (not code) -- stop" % (k, b, fn))
        break
    f0 = d[b - VA]; f1 = d[b + 1 - VA]; f2 = d[b + 2 - VA]
    v10 = u32(b + 0x10); v14 = u32(b + 0x14)
    v18 = u32(b + 0x18); v1c = u32(b + 0x1c)
    p58 = u32(b + 0x8); p5c = u32(b + 0xc)
    s58 = cstr(p58) if p58 else None
    s5c = cstr(p5c) if p5c else None
    print("  [%2d] base=0x%08X flags=%02x%02x%02x  +10=0x%08X +14=0x%08X  +18=0x%08X +1c=0x%08X  fn=0x%08X  str=%r/%r" % (
        k, b, f2, f1, f0, v10, v14, v18, v1c, fn, s58, s5c))
