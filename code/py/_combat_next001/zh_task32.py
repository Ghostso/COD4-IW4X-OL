# -*- coding: utf-8 -*-
"""找 0x62DE8F 函数（注册 task 0x32=回调 0x6379E0）的调用者。"""
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

F = 0x62DE90
print("=== direct callers of 0x62DE90 ===")
c = pe.calls_to(F)
print("   count = %d" % len(c))
for v in c:
    print("      %08X (in ~%s)" % (v, hex(fs(v)) if fs(v) else "?"))

print()
print("=== raw dword refs to 0x62DE90 (vtable?) ===")
h = pe.find_bytes(struct.pack("<I", F))
print("   count = %d" % len(h))
for o in h[:12]:
    v = pe.off_to_va(o)
    print("      fileoff=%08X va=%s" % (o, hex(v) if v else "-"))

print()
print("=== 0x62DE7F (sibling, push 0x26 -> 0x7FB240) callers ===")
for g in (0x62DE7F, 0x62DE80):
    c2 = pe.calls_to(g)
    print("   0x%08X -> %d" % (g, len(c2)))
    for v in c2[:10]:
        print("      %08X (in ~%s)" % (v, hex(fs(v)) if fs(v) else "?"))
    h2 = pe.find_bytes(struct.pack("<I", g))
    print("      data-refs: %s" % [hex(pe.off_to_va(o)) for o in h2[:6]])
