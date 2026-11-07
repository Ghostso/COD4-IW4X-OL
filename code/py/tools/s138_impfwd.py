#!/usr/bin/env python3
"""138: find sequences 'mov reg,[X+base_disp]' then 'call [reg+vtslot]' inside a range.
usage: s138_impfwd.py <lo> <hi> <base_disp_hex>
Prints each call through [reg+vtslot] where reg was loaded from [..+base_disp].
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True

lo = int(sys.argv[1], 0)
hi = int(sys.argv[2], 0)
base = int(sys.argv[3], 0)
code = d[lo - VA:hi - VA]
recent = {}
hist = []
for ins in md.disasm(code, lo):
    op = ins.op_str
    # mov reg, dword ptr [reg2 + base]
    if ins.mnemonic == "mov" and op.split(",")[0].strip() in (
            "eax", "ebx", "ecx", "edx", "esi", "edi") and "dword ptr [" in op:
        try:
            dst, src = op.split(",", 1)
            if "+" in src:
                disp = int(src.split("+")[1].split("]")[0].strip(), 16)
                if disp == base:
                    recent[dst.strip()] = ins.address
        except Exception:
            pass
    if ins.mnemonic == "call" and "dword ptr [" in op and "+" in op:
        try:
            inner = op[op.index("[") + 1:op.index("]")]
            reg = inner.split("+")[0].strip()
            slot = int(inner.split("+")[1].strip(), 16)
        except Exception:
            reg = None
        if reg in recent and ins.address - recent[reg] < 0x40:
            print("0x%08X  call [%s+0x%x]   (ptr from [..+0x%x] @0x%08X)" % (
                ins.address, reg, slot, base, recent[reg]))
    hist.append("x")
print("done")
