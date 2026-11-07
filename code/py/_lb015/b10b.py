# -*- coding: utf-8 -*-
import struct
import img
IMG = img._IMG; BASE = img.BASE
def hx(x): return "0x%X" % x
def findpat(p):
    out=[]; s=0
    while True:
        i=IMG.find(p,s)
        if i<0: break
        out.append(BASE+i); s=i+1
    return out
for name,p in (("word 28960 (20 71)", b"\x20\x71"),
               ("dword 28960", b"\x20\x71\x00\x00"),
               ("127.0.0.1 (7F000001)", b"\x7f\x00\x00\x01"),
               ("dword 0x00007120", b"\x20\x71\x00\x00")):
    r = findpat(p)
    print("%-24s count=%d  %s" % (name, len(r), [hx(x) for x in r[:40]]))
print()
# vtable slot for 0x7C5154 obj: disasm context
for insn in img.dis(0x7C5110, n=0x60):
    print("  %08X %-18s %s" % (insn.address, insn.bytes.hex(), insn.mnemonic+" "+insn.op_str))
    if insn.address >= 0x7C5160: break
