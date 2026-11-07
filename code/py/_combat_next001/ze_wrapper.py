# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def fs(va):
    for back in range(1, 0x1500):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC: return x + 1
    return None

TGT = 0x6379E0
print("=== direct E8 callers of 0x6379E0 (the wrapper) ===")
c = pe.calls_to(TGT)
print("   count = %d" % len(c))
for v in c:
    print("      %08X (in ~%s)" % (v, hex(fs(v)) if fs(v) else "?"))

print()
print("=== all raw dword refs to 0x6379E0 ===")
hits = pe.find_bytes(struct.pack("<I", TGT))
print("   count = %d" % len(hits))
for o in hits[:20]:
    v = pe.off_to_va(o)
    sec = pe.section_of(v) if v else None
    print("      fileoff=%08X va=%s sect=%s" % (o, hex(v) if v else "-", sec.name if sec else "?"))

print()
print("=== also 0x6379DF (pad) refs? ===")
h2 = pe.find_bytes(struct.pack("<I", 0x6379DF))
print("   count = %d %s" % (len(h2), [hex(pe.off_to_va(o)) for o in h2[:6]]))
