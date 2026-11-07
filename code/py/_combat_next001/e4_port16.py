# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def hits(pat, label, maxn=40):
    print("--- %s ---" % label)
    n = 0
    for o in pe.find_bytes(pat):
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            n += 1
            if n <= maxn:
                print("   %08X" % va)
    print("   total=%d" % n)
    return n

# 0x2071 little-endian = 71 20   (host order, used by mov ax,imm / and / or / cmp)
hits(b"\x66\xb8\x71\x20", "mov ax, 0x2071")
hits(b"\x66\x68\x71\x20", "pushw 0x2071")
hits(b"\x66\x3d\x71\x20", "cmp ax, 0x2071")
hits(b"\x66\xbd\x71\x20", "mov bp, 0x2071")
# big-endian form 20 71 (network byte order) in 16-bit immediate
hits(b"\x66\xb8\x20\x71", "mov ax, 0x7120")
hits(b"\x66\x68\x20\x71", "pushw 0x7120")
# 32-bit 0x2071 with zero-extension patterns already covered; also test 'mov word [mem], 0x2071'
hits(b"\x66\xc7", "mov word ptr [..], imm16 (generic count)", maxn=0)
print()
print("=== any occurrence of the byte pair 71 20 in code, annotated ===")
n = 0
for o in pe.find_bytes(b"\x71\x20"):
    va = pe.off_to_va(o)
    if va and pe.is_exec(va):
        n += 1
        if n <= 30:
            print("   %08X  ctx=%s" % (va - 1, pe.read(va - 6, 12).hex()))
print("   total=%d" % n)
