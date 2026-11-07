# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== caller 0x62CD8B context (second path into the battle bridge) ===")
for l in pe.dis(0x62CD50, 35):
    print(l)
print()
print("=== data at 0xDC73B0 / 0xDC7850 (candidate vtables) ===")
for va in (0xDC73B0, 0xDC7850):
    print("  %08X: %s" % (va, pe.read(va, 48).hex()))
print()
print("=== enclosing func of 0x62CD8B (scan back for int3 pad) ===")
site = 0x62CD8B
for back in range(1, 0x1500):
    va = site - back
    b = pe.read(va, 2)
    if b and b[0] == 0xCC and b[1] == 0xCC:
        print("   ~%08X" % (va + 1)); break
print()
print("=== 0x5C05F0 state machine: which state value reaches case0 (getchallenge)? ===")
print("   0x5C068D: cmp byte [esi+0x278],0 ; je bail   (per-frame gate A)")
print("   0x5C069B: cmp [0x76446b0],3   ; jge bail   (gate B: [0x76446b0] must be < 3)")
print("   0x5C0620+: eax=[0x76446b0]; must be 3,4,5,6 -> switch(eax-3)")
print("   => [0x76446b0]==3 is the ONLY value that yields case0 = getchallenge")
