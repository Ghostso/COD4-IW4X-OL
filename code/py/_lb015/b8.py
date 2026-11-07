# -*- coding: utf-8 -*-
import sys, struct
import fast, img, mem
from img import dword as IDW, read as IRD, call_rel32_hits
M = mem.M
def hx(x): return "0x%X" % x

print("== remaining insert contexts ==")
for c in (0x63B097,0x7C509B,0x724E44,0x736CD5):
    print("----- 0x%X -----" % c)
    for insn in img.dis(c-0x38, n=0x38+12):
        if c-0x38 <= insn.address <= c+3:
            print("  %08X %-20s %s" % (insn.address, insn.bytes.hex(), insn.mnemonic+" "+insn.op_str))
    print()

def vt_of(obj):
    v1 = IDW(obj)
    v2 = M.dword(obj)
    return v1, v2

print("== vtable +0x24 of candidate listener objects ==")
for obj in (0xE60CAF8, 0xE69CB0, 0xE69BE0):
    v1, v2 = vt_of(obj)
    print("obj %s : image[obj]=%s  dump[obj]=%s" % (hx(obj), hx(v1) if v1 else None, hx(v2) if v2 else None))

print()
print("== dump availability around E60, E69 ==")
for base in (0xE600000, 0xE690000, 0xE6A0000):
    print(hex(base), M.find(base), M.find(base+0xFC))

print()
print("== vtable 0xDC78EC and 0xDC78EC+0x24 ==")
for vt in (0xDC78EC,):
    for i in range(16):
        v = IDW(vt+4*i)
        print("  +0x%02X = %s" % (4*i, hx(v)))
