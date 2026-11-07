#!/usr/bin/env python3
"""s138_full_store: linear-sweep the code section and report STORES to memory
operands with a given disp. Handles both disp8 and disp32 forms.
Usage: python -I tools/s138_full_store.py 0x20 0x24 ...
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
md.skipdata = True

disps = {int(x, 0) for x in sys.argv[1:]}
lo, hi = 0x1000, 0x8A8000          # .tp3 first section raw range
code = d[lo:hi]

n = 0
for ins in md.disasm(code, VA + lo):
    if ins.mnemonic not in ("mov", "movzx", "movsx", "movsxd", "and", "or", "xor", "add", "sub", "inc", "dec", "fld", "fstp", "fst", "fadd", "fsub"):
        continue
    if not ins.operands:
        continue
    op = ins.operands[0]
    if op.type != X86_OP_MEM or op.mem.disp not in disps:
        continue
    print("  0x%08X  %-26s %-6s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    n += 1
print("total %d" % n)
