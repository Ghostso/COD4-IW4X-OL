#!/usr/bin/env python3
"""s138_keyfind: 在 E37xxxx descriptor 区找 (svc,task) 键 (小整数) + 代码指针 的对象."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a

def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

lo, hi = 0xE370000, 0xE37D000
print("=== objects with small svc/task at +0x10/+0x14 ===")
hits = []
for base in range(lo, hi, 4):
    s = u32(base + 0x10); t = u32(base + 0x14)
    if s is None or t is None: continue
    if not (0 <= s <= 200 and 1 <= t <= 200): continue
    # some code pointer in the record
    codes = [u32(base + 4 * k) for k in range(0, 0x25d0 // 4)]
    codes = [c for c in codes if c and TL <= c < TH]
    if codes:
        hits.append((base, s, t, codes[:4]))

# dedupe by (s,t)
seen = set()
for base, s, t, codes in hits:
    key = (s, t, base)
    if (s, t) in seen: continue
    if s in (6,) or (s, t) == (6, 5):
        print("  base=0x%08X svc=%-3d task=%-3d codes=%s" % (base, s, t, [hex(c) for c in codes]))
        seen.add((s, t))
print("total hits", len(hits))
# also print all distinct (svc,task) seen
print("distinct (svc,task):", sorted(set((s, t) for _, s, t, _ in hits))[:80])
