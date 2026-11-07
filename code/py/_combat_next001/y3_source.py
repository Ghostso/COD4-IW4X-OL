# -*- coding: utf-8 -*-
"""定位 [mk+0x10728] 结构（槽数据源）的填充点，以及全局 0x82E13FC 的写入。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
R = "eax ecx edx ebx esp ebp esi edi".split()

def scan_disp(disp):
    res = []
    for o in range(len(d) - 7):
        op = d[o]
        if op not in (0x88,0x89,0x8B,0x8D,0xC6,0xC7): continue
        m = d[o+1]
        if (m >> 6) != 2 or (m & 7) == 4: continue
        if struct.unpack_from("<i", d, o+2)[0] != disp: continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            res.append((op, va, m & 7, (m >> 3) & 7))
    return res

def fs(va):
    for back in range(1, 0x1200):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC: return x + 1
    return None

print("=== +0x10728 的写入 / lea ===")
for op, va, rm, src in sorted(scan_disp(0x10728)):
    kind = {0x88:"movb [.]",0x89:"mov [.]",0x8B:"mov r,[.]",0x8D:"lea",0xC6:"movb imm",0xC7:"mov imm"}[op]
    print("   %08X  %-10s [%s+0x10728]  src=%s  (func ~%s)" % (
        va, kind, R[rm], R[src], ("%08X"%fs(va)) if fs(va) else "?"))

print()
print("=== 全局 0x82E13FC 的写入点 ===")
n = 0
for pre in (b"\x89\x05", b"\xa3", b"\xc7\x05"):
    for o in pe.find_bytes(pre + struct.pack("<I", 0x82E13FC)):
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            n += 1; print("   %08X  (func ~%s)" % (va, ("%08X"%fs(va)) if fs(va) else "?"))
print("   total =", n)

print()
print("=== 0x82E13FC 附近的全局数组（0x82E13xx..0x82E14xx 的引用者） ===")
for base in (0x82E13FC, 0x82E140C, 0x82E1424, 0x82E1404, 0x82E1410, 0x82E1414):
    hits = [pe.off_to_va(o) for o in pe.find_bytes(struct.pack("<I", base))]
    hits = [h for h in hits if h and pe.is_exec(h)]
    print("   %08X -> %d refs" % (base, len(hits)))
