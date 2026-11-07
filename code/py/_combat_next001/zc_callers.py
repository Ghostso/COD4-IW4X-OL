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

print("=== entry check: bytes at 0x63794F / 0x637950 ===")
print("   0x63794F: " + pe.read(0x63794F, 4).hex())
print("   0x637950: " + pe.read(0x637950, 4).hex())
print("   function start = %s" % (hex(fs(0x637950)) if fs(0x637950) else "?"))

print()
print("=== direct E8 callers of 0x63794F / 0x637950 ===")
for t in (0x63794F, 0x637950):
    c = pe.calls_to(t)
    print("   0x%08X -> %d direct callers" % (t, len(c)))
    for v in c:
        print("      %08X (in ~%s)" % (v, hex(fs(v)) if fs(v) else "?"))

print()
print("=== all raw dword refs to 0x63794F and 0x637950 ===")
for t in (0x63794F, 0x637950):
    hits = pe.find_bytes(struct.pack("<I", t))
    print("   0x%08X -> %d refs" % (t, len(hits)))
    for o in hits[:12]:
        v = pe.off_to_va(o)
        sec = pe.section_of(v) if v else None
        print("      fileoff=%08X va=%s sect=%s" % (o, hex(v) if v else "-", sec.name if sec else "?"))
