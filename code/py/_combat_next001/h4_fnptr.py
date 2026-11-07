# -*- coding: utf-8 -*-
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data

print("=== call dword ptr [imm32] sites where the slot is > 0xE00000 (module-private fnptr tables) ===")
cnt = collections.Counter()
for o in range(len(d) - 6):
    if d[o] == 0xFF and d[o+1] == 0x15:
        tgt = struct.unpack_from("<I", d, o+2)[0]
        va = pe.off_to_va(o)
        if va and pe.is_exec(va) and tgt > 0xE00000:
            cnt[tgt] += 1
for tgt, n in cnt.most_common(30):
    print("   [0x%08X] x%d" % (tgt, n))

print()
print("=== indirect call via register slots: 'call dword ptr [reg+disp]' count by disp ===")
cnt2 = collections.Counter()
for o in range(len(d) - 3):
    if d[o] == 0xFF and (d[o+1] & 0x38) == 0x10:   # /2 = call
        modrm = d[o+1]; mod = modrm >> 6; rm = modrm & 7
        if rm == 4: continue
        if mod == 1:
            disp = struct.unpack_from("<b", d, o+2)[0]
        elif mod == 2:
            disp = struct.unpack_from("<i", d, o+2)[0]
        elif mod == 0:
            disp = 0
        else:
            continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            cnt2[disp] += 1
for disp, n in cnt2.most_common(20):
    print("   [reg+0x%X] x%d" % (disp, n))
