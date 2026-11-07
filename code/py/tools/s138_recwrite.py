#!/usr/bin/env python3
"""s138_recwrite: linear-scan a VA range for stores into [reg+0x28]/[reg+0x2c]
and [reg+0x18]/[reg+0x1c], which are the srpc record svc/task fields.
Usage: python -I tools/s138_recwrite.py <lo> <hi>
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

lo = int(sys.argv[1], 0)
hi = int(sys.argv[2], 0)
pats = ("+ 0x28]", "+ 0x2c]", "+ 0x18]", "+ 0x1c]")
for ins in md.disasm(d[lo - VA:hi - VA], lo):
    if ins.mnemonic != "mov":
        continue
    if not ins.op_str.startswith("dword ptr ["):
        continue
    if any(p in ins.op_str for p in pats):
        print("0x%08X  %-20s %s" % (ins.address, ins.bytes.hex(), ins.op_str))
