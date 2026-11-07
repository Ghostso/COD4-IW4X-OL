# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== ALL raw occurrences of dword 0x00470360 in the whole file ===")
for o in pe.find_bytes(struct.pack("<I", 0x470360)):
    print("   fileoff=%08X va=%s" % (o, hex(pe.off_to_va(o)) if pe.off_to_va(o) else "-"))
print()
print("=== 0x5C05F0 ===")
for o in pe.find_bytes(struct.pack("<I", 0x5C05F0)):
    print("   fileoff=%08X va=%s" % (o, hex(pe.off_to_va(o)) if pe.off_to_va(o) else "-"))
print()
print("=== 0x5BEAEA / 0x5C2AB9 callers: what function are they in? ===")
for site in (0x5BEAEA, 0x5C2AB9):
    for back in range(1, 0x1000):
        va = site - back
        b = pe.read(va, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC:
            print("   %08X is inside function starting ~%08X" % (site, va + 1))
            break
print()
print("=== what calls 0x47035F's neighbourhood: scan for call sites near 0x4703xx ===")
for o in pe.find_bytes(b"\xe8"):
    if o + 5 > len(pe.data): continue
    rel = struct.unpack_from("<i", pe.data, o + 1)[0]
    va = pe.off_to_va(o)
    if not va or not pe.is_exec(va): continue
    t = va + 5 + rel
    if 0x470300 <= t <= 0x470380:
        print("   call %08X -> %08X" % (va, t))
