# -*- coding: utf-8 -*-
"""决定性检索：任何写入 [+0x168]/[+0x16C] 的地方（不限结构），
   重点看是否落在网络/序列化区 (0x80xxxx / 0xB7xxxx) 且邻近 0x238 常量。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
R = "eax ecx edx ebx esp ebp esi edi".split()

def fs(va):
    for back in range(1, 0x1800):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC: return x + 1
    return None

def scan_writes(disp):
    out = []
    for o in range(len(d) - 7):
        op = d[o]
        if op not in (0x88, 0x89, 0xC6, 0xC7, 0x66): continue
        off = 1
        if op == 0x66:
            if d[o+1] != 0x89: continue
            off = 2
        m = d[o+off]
        if (m >> 6) != 2 or (m & 7) == 4: continue
        if struct.unpack_from("<i", d, o+off+1)[0] != disp: continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va): out.append(va)
    return sorted(set(out))

for disp in (0x168, 0x16C):
    hits = scan_writes(disp)
    print("=== 写 [+0x%X] 的全部点 : %d ===" % (disp, len(hits)))
    net = []
    for va in hits:
        f = fs(va)
        reg = "net" if f and (0x800000 <= f <= 0x81FFFF or 0xB70000 <= f <= 0xCB0000) else ""
        if reg: net.append((va, f))
        print("   %08X (func ~%s) %s" % (va, hex(f) if f else "?", reg))
    print("   ==> 网络/序列化区命中 = %d %s" % (len(net), [(hex(a), hex(b)) for a, b in net]))
    print()
