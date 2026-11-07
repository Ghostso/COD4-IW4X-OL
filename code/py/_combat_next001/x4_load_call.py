# -*- coding: utf-8 -*-
"""找 'mov reg,[base+0x28]' 之后紧接着 'call reg' 的组合（回调消费点候选）。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
R = "eax ecx edx ebx esp ebp esi edi".split()
CALLR = {0xD0:0,0xD1:1,0xD2:2,0xD3:3,0xD4:4,0xD5:5,0xD6:6,0xD7:7}

def find_mov_read(disp):
    """返回 (va, base_reg, dst_reg) for 'mov dst,[base+disp]'。"""
    out = []
    for o in range(len(d) - 7):
        if d[o] != 0x8B: continue
        m = d[o+1]
        if (m >> 6) != 1: continue
        rm = m & 7
        if rm in (4, 5): continue
        if struct.unpack_from("<b", d, o+2)[0] != disp: continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            out.append((va, rm, (m >> 3) & 7))
    return out

cands = []
for va, base, dst in find_mov_read(0x28):
    # 在接下来 48 字节内找 call dst_reg
    for k in range(0, 48):
        p = va + k
        b = pe.read(p, 2)
        if not b: break
        if b[0] == 0xFF and b[1] in CALLR and CALLR[b[1]] == dst:
            cands.append((va, p, base, dst))
            break
        # 允许 push dst 作为参数后再 call [reg]
        if b[0] == 0xFF and (b[1] & 0x38) == 0x10:
            cands.append((va, p, base, dst))
            break

print("=== 'mov dst,[base+0x28]' 后 48B 内出现间接 call 的候选：%d 个 ===" % len(cands))
for va, callva, base, dst in cands[:60]:
    print("   load %08X (mov %s,[%s+0x28])  ->  call/ind %08X" % (va, R[dst], R[base], callva))
print()
print("=== 其中落在网络/传输区 (0xB7xxxx..0xCBxxxx) 的 ===")
for va, callva, base, dst in cands:
    if 0xB70000 <= va <= 0xCB0000:
        print("   load %08X (mov %s,[%s+0x28])  ->  %08X" % (va, R[dst], R[base], callva))
