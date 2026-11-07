# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x806B50 (called for every slot region during init) ===")
for l in pe.dis(0x806B50, 25):
    print(l)
print()
print("=== 0x623770 (called for +0xe368 region) ===")
for l in pe.dis(0x623770, 18):
    print(l)
print()
print("=== ALL memcpy-like calls (E8 -> 0xC427F0) whose dst is derived from +0x7470 ===")
# 找 lea reg,[reg+0x7470] 之后的 push 序列
for o in pe.find_bytes(b"\x8d"):
    pass
import re
# 直接列出 lea ...[+0x7470] 的全部位置与所属函数
hits = []
for o in range(len(pe.data) - 7):
    if pe.data[o] != 0x8D: continue
    m = pe.data[o+1]
    if (m >> 6) != 2: continue
    if struct.unpack_from("<i", pe.data, o+2)[0] != 0x7470: continue
    va = pe.off_to_va(o)
    if va and pe.is_exec(va): hits.append(va)
print("   lea ...,[reg+0x7470] 命中 = %d" % len(hits))
for va in hits:
    for back in range(1, 0x1200):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC:
            print("      %08X  (func ~%08X)" % (va, x+1)); break
