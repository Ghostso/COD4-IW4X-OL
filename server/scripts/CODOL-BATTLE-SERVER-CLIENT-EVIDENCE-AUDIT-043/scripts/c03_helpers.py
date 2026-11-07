# -*- coding: utf-8 -*-
"""Corrected helper disassembly (RVA = VA - 0x400000). Read-only."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
out=[]
def emit(s): out.append(s)
def show(va,n,label):
    rva=va-C.IBI
    emit("=== %s  VA=%08x RVA=%08x ==="%(label,va,rva))
    for k in C.idis_range(rva,rva+n):
        emit("  %08x  %-16s %-8s %s"%(k.address-C.IBI,k.bytes.hex(),k.mnemonic,k.op_str))
show(0xB44B20,0x20,"is-netfield? (F-A:0x87A8AD)")
show(0xBCD790,0x28,"unit-byte-width 0xBCD790")
show(0xBCD950,0x40,"estimate 0xBCD950 (F-B:0x87AA53)")
show(0xBCD7C0,0x70,"encode/decode core 0xBCD7C0")
io.open(os.path.join(C.EV,"c_helpers_corrected.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
