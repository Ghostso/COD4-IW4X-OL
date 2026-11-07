# -*- coding: utf-8 -*-
import sys, struct
import img, mem
from img import dword as IDW, read as IRD, call_rel32_hits, BASE
M = mem.M

def callers(target):
    res = {}
    # image_best
    ib = set(call_rel32_hits(target))
    # dump: scan code regions
    du = set()
    for (s, sz, data) in M.regions:
        for i in range(0, len(data)-5):
            if data[i] == 0xE8:
                rel = struct.unpack_from("<i", data, i+1)[0]
                if s + i + 5 + rel == target:
                    du.add(s+i)
    return sorted(ib), sorted(du)

for t in (0x638210,):
    ib, du = callers(t)
    print("=== callers of 0x%X ===" % t)
    print("image_best:", [hex(x) for x in ib])
    print("dump      :", [hex(x) for x in du])
