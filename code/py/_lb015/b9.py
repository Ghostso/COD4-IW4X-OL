# -*- coding: utf-8 -*-
import sys, struct
import fast, img, mem
from img import dword as IDW, read as IRD
M = mem.M
def hx(x): return "0x%X" % x

print("== E6 dump coverage ==")
for va in (0xE60CAF8,0xE69C34,0xE69CB0,0xE69BE0,0xE6F8C4,0xE6F014,0xE6F890):
    r = M.dword(va)
    print("  %s -> %s" % (hx(va), hx(r) if r is not None else "UNREADABLE"))

def show_vt(vt, n=10, label=""):
    print("--- vtable %s %s ---" % (hx(vt), label))
    for i in range(n):
        v = IDW(vt+4*i) if (vt+4*i < 0xE65000) else M.dword(vt+4*i)
        print("  +0x%02X = %s" % (4*i, hx(v) if v is not None else "?"))

def show_fn(a, n=0x30, label=""):
    print("--- fn %s %s ---" % (hx(a), label))
    if a is None: return
    if 0x401000 <= a < 0xE65000:
        ins = img.dis(a, n=n)
    else:
        ins = M.dis(a, n=n)
    cnt=0
    for insn in ins:
        print("  %08X %-20s %s" % (insn.address, insn.bytes.hex(), insn.mnemonic+" "+insn.op_str))
        cnt+=1
        if cnt>26: break

for obj, label in ((0xE60CAF8,"global"),(0xE69C34,"global"),(0xE69CB0,"global"),(0xE69BE0,"global")):
    vt = M.dword(obj)
    print("obj %s [%s]=vtable %s" % (hx(obj), label, hx(vt) if vt is not None else "?"))
    if vt and vt < 0xE65000:
        show_vt(vt, 10)
        f = IDW(vt+0x24)
        print("   +0x24 = %s" % hx(f))
        show_fn(f)

print()
for vt,label in ((0xDC78EC,"0xE60CAF8 vt"),(0xDCECEC,"6C0E43 obj vt")):
    show_vt(vt, 12, label)
    f = IDW(vt+0x24)
    print("   +0x24 = %s" % hx(f))
    show_fn(f)
