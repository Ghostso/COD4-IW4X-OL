# -*- coding: utf-8 -*-
import sys, struct
import fast, img, mem
from img import dword as IDW, read as IRD, call_rel32_hits
M = mem.M
def hx(x): return "0x%X" % x

callers = [0x623452,0x6382B3,0x6382D9,0x63B097,0x63B4E7,0x6C0E43,0x6C2E66,0x724E44,0x736CD5,0x7C509B,0x7C5154,0x7CBCF6,0x7E99DA]
for c in callers:
    print("===== caller 0x%X  (context) =====" % c)
    start = c - 0x60
    ins = img.dis(start, n=0x60+16)
    for insn in ins:
        if c-0x60 <= insn.address <= c+6:
            print("  %08X %-20s %s" % (insn.address, insn.bytes.hex(), insn.mnemonic+" "+insn.op_str))
    print()

print("== 0x82E13FC refs >= 0x630000 (image) ==")
print([hx(x) for x in img.dword_refs(0x82E13FC) if x >= 0x630000])
print("== 0x82E13FC refs >= 0xE00000 (image) ==")
print([hx(x) for x in img.dword_refs(0x82E13FC) if x >= 0xE00000])
print("== 0x82E1400 refs >= 0x630000 (image) ==")
print([hx(x) for x in img.dword_refs(0x82E1400) if x >= 0x630000])
print("== 0x82E1400 refs >= 0xE00000 (image) ==")
print([hx(x) for x in img.dword_refs(0x82E1400) if x >= 0xE00000])
