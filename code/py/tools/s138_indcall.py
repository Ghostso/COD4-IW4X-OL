#!/usr/bin/env python3
"""138: list indirect 'call dword ptr [reg+disp]' within a VA range,
with the preceding 2 instructions for context."""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

lo = int(sys.argv[1], 0)
hi = int(sys.argv[2], 0)
code = d[lo - VA:hi - VA]
hist = []
for ins in md.disasm(code, lo):
    s = "%s %s" % (ins.mnemonic, ins.op_str)
    if ins.mnemonic == "call" and "dword ptr [" in ins.op_str and "+" in ins.op_str:
        print("0x%08X  %-30s || %s" % (ins.address, s, " ; ".join(hist[-3:])))
    hist.append("0x%08X %s" % (ins.address, s))
