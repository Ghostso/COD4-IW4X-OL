# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== every raw dword reference to 0x62CD30 ===")
for o in pe.find_bytes(struct.pack("<I", 0x62CD30)):
    va = pe.off_to_va(o)
    sec = pe.section_of(va) if va else None
    print("   fileoff=%08X va=%s sect=%s" % (o, hex(va) if va else "-", sec.name if sec else "?"))

print()
print("=== every raw dword reference to 0x637590 / 0x637720 / 0x6376F0 ===")
for t in (0x637590, 0x637720, 0x6376F0):
    print("  -- 0x%08X --" % t)
    hits = pe.find_bytes(struct.pack("<I", t))
    print("     count=%d" % len(hits))
    for o in hits[:8]:
        va = pe.off_to_va(o)
        print("     fileoff=%08X va=%s" % (o, hex(va) if va else "-"))

print()
print("=== who calls 0x62CD30 directly (E8) ===")
for v in pe.calls_to(0x62CD30):
    print("   %08X" % v)
