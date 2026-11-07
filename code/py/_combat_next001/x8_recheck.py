# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data

fn = 0x62DD60          # real entry (0x62DD5F is the int3 pad)
print("=== scan vtable 0xDC7274 .. +0x400 for 0x%08X ===" % fn)
for i in range(0, 0x100):
    va = 0xDC7274 + i*4
    b = pe.read(va, 4)
    if not b: break
    if struct.unpack("<I", b)[0] == fn:
        print("   primary vtable slot +0x%03X = 0x%08X" % (i*4, fn))

print()
print("=== every dword ref to 0x62DD60 anywhere ===")
for o in pe.find_bytes(struct.pack("<I", fn)):
    v = pe.off_to_va(o)
    print("   fileoff=%08X va=%s" % (o, hex(v) if v else "-"))

print()
print("=== every dword ref to 0x6376F0 and 0x637930 (recheck with exact entries) ===")
for t in (0x6376F0, 0x6376F1, 0x637930, 0x637931):
    hits = pe.find_bytes(struct.pack("<I", t))
    print("   0x%08X -> %d refs %s" % (t, len(hits), [hex(pe.off_to_va(o)) for o in hits[:5]]))
