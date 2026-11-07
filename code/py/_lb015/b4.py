# -*- coding: utf-8 -*-
import sys, struct
import fast, img, mem
from img import dword as IDW, read as IRD, call_rel32_hits
M = mem.M
def hx(x): return "0x%X" % x

print("===== DISASM 0x724EB0 (insert helper) =====")
for ins in img.dis(0x724EB0, count=60):
    print("  %08X %-22s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic+" "+ins.op_str))
    if ins.address > 0x724F60: break

print()
print("===== DISASM 0x639D00 (init) =====")
for ins in img.dis(0x639D00, count=140):
    print("  %08X %-22s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic+" "+ins.op_str))
    if ins.address > 0x639EC0: break
