# -*- coding: utf-8 -*-
"""Disassemble the helpers called by 0x87A890, using RVA = VA - 0x400000. Read-only."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
out=[]
def emit(s): out.append(s)
def show(va, n, label):
    rva=va-C.IBI
    emit("=== %s  VA=%08x RVA=%08x  in_image=%s ==="%(label,va,rva,rva<len(C._bi)))
    for k in C.idis_range(rva, rva+n):
        emit("  %08x  %-16s %-8s %s"%(k.address-C.IBI,k.bytes.hex(),k.mnemonic,k.op_str))
show(0xB44B20, 0x60, "helper 0xB44B20 (F-A:0x87A8AD)")
show(0xBCD790, 0x50, "helper 0xBCD790 (F-A:0x87A8C1/0x87A9AF)")
show(0xBCD950, 0x50, "helper 0xBCD950 (F-B:0x87AA53)")
io.open(os.path.join(C.EV,"dis_sizeinfo_helpers.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
