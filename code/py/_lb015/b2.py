# -*- coding: utf-8 -*-
import sys, struct
import fast, img, mem
from img import dword as IDW, read as IRD, call_rel32_hits
M = mem.M
def hx(x): return "0x%X" % x

print("===== FULL DISASM 0x632680 (accepted handler) =====")
for ins in img.dis(0x632680, count=260):
    print("  %08X %-22s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic+" "+ins.op_str))
    if ins.address > 0x6329C0:
        break
