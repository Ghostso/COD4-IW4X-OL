# -*- coding: utf-8 -*-
import struct
import img
from img import dword as IDW, read as IRD
def hx(x): return "0x%X" % x

print("===== 0x7CAF30 (listener E69CB0 +0x24) =====")
for insn in img.dis(0x7CAF30, n=0x140):
    print("  %08X %-18s %s" % (insn.address, insn.bytes.hex(), insn.mnemonic+" "+insn.op_str))
    if insn.address >= 0x7CB070: break
