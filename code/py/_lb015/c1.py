# -*- coding: utf-8 -*-
import struct
import fast, img, mem
from img import dword as IDW, read as IRD
M = mem.M
def hx(x): return "0x%X" % x
def rd(va):
    return IDW(va) if 0x400000<=va<0xE65000 else M.dword(va)
def show(a,n=0x50,label=""):
    print("--- %s %s ---"%(hx(a),label))
    if a is None: return
    ins = img.dis(a,n=n) if 0x401000<=a<0xE65000 else M.dis(a,n=n)
    cnt=0
    for i in ins:
        print("  %08X %-18s %s"%(i.address,i.bytes.hex(),i.mnemonic+" "+i.op_str)); cnt+=1
        if cnt>24: break

o = rd(0x849B60C)
print("== [0x849B60C] obj =", hx(o) if o else None)
if o:
    vt = rd(o); print("vt =", hx(vt))
    if vt:
        for i in range(10): print("   +0x%02X = %s"%(4*i, hx(rd(vt+4*i))))
        show(rd(vt+0x24), label="+0x24")
print()
show(0x63B020, n=0x50, label="0x63B020 (find esi for 0x63B097)")
