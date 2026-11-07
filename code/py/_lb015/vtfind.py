# -*- coding: utf-8 -*-
import img, struct
d = img._IMG; BASE=0x400000
CODE_LO, CODE_HI = 0x401000, 0x8A789A
def is_code(v): return CODE_LO <= v <= CODE_HI
# collect candidate vtables: V such that [V..V+0x60] are code pointers (>=8)
cand = {}
n = len(d)
for i in range(0, n-4, 4):
    v = struct.unpack_from("<I", d, i)[0]
    if 0xD00000 <= v <= 0xE65000:
        cand.setdefault(v, []).append(BASE+i)
print("candidate V values:", len(cand))
vtables = []
for v, srcs in cand.items():
    off = v - BASE
    if off < 0 or off+0x80 > n: continue
    vals = struct.unpack_from("<32I", d, off)
    if all(is_code(x) for x in vals[:8]) and is_code(vals[9]):
        vtables.append((v, srcs))
print("confirmed vtables:", len(vtables))
import json
out=[]
for v, srcs in sorted(vtables):
    slot24 = struct.unpack_from("<I", d, v-BASE+0x24)[0]
    out.append((v, slot24, len(srcs), srcs[:4]))
for v, s24, c, srcs in out:
    print("vt=%08X slot+24=%08X refs=%d first=%s" % (v, s24, c, " ".join("%08X"%x for x in srcs)))
