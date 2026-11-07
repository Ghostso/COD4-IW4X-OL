# -*- coding: utf-8 -*-
"""搜索 0x238 / 0x8E 常量的全部使用点，定位 0x238 记录的分配与复制。"""
import sys, os, struct, collections
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

def imm_hits(val, label):
    res = []
    for pre, kind in ((b"\x68","push"),(b"\xb8","mov eax"),(b"\xb9","mov ecx"),
                      (b"\xba","mov edx"),(b"\xbb","mov ebx"),(b"\xbe","mov esi"),
                      (b"\xbf","mov edi"),(b"\x6a","push8")):
        pat = pre + (struct.pack("<I", val) if pre != b"\x6a" else bytes([val & 0xFF]))
        if val > 0x7F and pre == b"\x6a": continue
        for o in pe.find_bytes(pat):
            va = pe.off_to_va(o)
            if va and pe.is_exec(va):
                res.append((kind, va))
    print("=== %s (0x%X) : %d hit ===" % (label, val, len(res)))
    for kind, va in sorted(res, key=lambda x: x[1]):
        f = fs(va)
        print("   %08X %-8s (func ~%s)" % (va, kind, hex(f) if f else "?"))
    print()
    return res

imm_hits(0x238, "record size")
imm_hits(0x8E, "142 dwords = 0x238 B")
