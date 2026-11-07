#!/usr/bin/env python3
"""138: find calls through [reg+disp] with given disp (any register).
usage: s138_vtslot.py <disp_hex> [lo] [hi]
"""
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

slot = int(sys.argv[1], 0)
lo = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x401000
hi = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x401000 + 0x8a689a

code = d[lo - VA:hi - VA]
hist = []
n = 0
pat = re.compile(r"\[\w+\s*\+\s*0x%x\]" % slot)
for ins in md.disasm(code, lo):
    if ins.mnemonic in ("call", "jmp") and pat.search(ins.op_str):
        n += 1
        print("0x%08X  %-26s || %s" % (ins.address, ins.mnemonic + " " + ins.op_str,
                                        " ; ".join(hist[-4:])))
    hist.append("0x%08X %s %s" % (ins.address, ins.mnemonic, ins.op_str))
print("TOTAL", n)
