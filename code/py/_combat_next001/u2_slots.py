# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

interesting = {0x6292B0:"mmbook-response/notify handler?", 0x6293B0:"BRIDGE (accepted->battle)",
               0x632680:"mmbook accepted handler", 0x62F840:"battle-booking entry",
               0x62CD30:"reservation slot FILLER", 0x62F6F0:"mmbook cmd builder",
               0x6376F0:"slot filler entry", 0x637590:"slot writer (in)",
               0x637720:"slot writer (2)", 0x6292F0:"?", 0x631E50:"?", 0x632070:"mmstart ctor"}

print("=== which vtable slots hold our key functions? (both vtables) ===")
for base in (0xDC72B0, 0xDC7750):
    print("  -- vtable 0x%08X --" % base)
    for i in range(0, 0x90):
        v = struct.unpack("<I", pe.read(base + i*4, 4))[0]
        if v in interesting:
            print("     slot +0x%03X = %08X   %s" % (i*4, v, interesting[v]))
    print()

print("=== find all functions in 0x628000..0x63A000 referenced by data (vtable members) ===")
# 已在上面覆盖；此处列出 0x629xxx 家族的数据引用
for t in (0x6292B0, 0x6293B0, 0x6292F0, 0x629320):
    hits = []
    for o in pe.find_bytes(struct.pack("<I", t)):
        v = pe.off_to_va(o)
        hits.append((o, v))
    print("  0x%08X data-refs=%d %s" % (t, len(hits), [hex(v) if v else '-' for _, v in hits[:6]]))
