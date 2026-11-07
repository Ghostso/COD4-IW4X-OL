# -*- coding: utf-8 -*-
import img, struct, re
d = img._IMG; BASE=0x400000
CODE_LO, CODE_HI = 0x401000, 0x8A789A
def is_code(v): return CODE_LO <= v <= CODE_HI
n = len(d)
found = []
for i in range(2, n-4):
    v = struct.unpack_from("<I", d, i)[0]
    if not (0xD00000 <= v <= 0xE65000): continue
    if d[i-2] != 0xC7: continue
    m = d[i-1]
    if (m & 0xC0) != 0x00: continue
    if ((m >> 3) & 7) != 0: continue
    off = v - BASE
    if off < 0 or off+0x80 > n: continue
    vals = struct.unpack_from("<32I", d, off)
    if all(is_code(x) for x in vals[:10]):
        found.append((BASE+i, v))
        continue
    if all(is_code(x) for x in vals[:6]):
        found.append((BASE+i, v))
vts = {}
for src, v in found:
    vts.setdefault(v, []).append(src)
print("distinct vtables:", len(vts))
for v in sorted(vts):
    off=v-BASE
    vals = struct.unpack_from("<32I", d, off)
    slot24 = vals[9]
    print("vt=%08X slot+24=%08X srcs=%s" % (v, slot24, " ".join("%08X"%x for x in vts[v])))
