#!/usr/bin/env python3
"""138: robust whole-text scan with skipdata, tracking vtable-style calls.
usage: s138_fwd2.py [disp_filter_hex]
Finds: call reg where reg was loaded from [reg2+disp] shortly before.
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True

lo = 0x401000
hi = 0x401000 + 0x8a689a
flt = int(sys.argv[1], 0) if len(sys.argv) > 1 else None

code = d[lo - VA:hi - VA]
recent = {}
n = 0
for ins in md.disasm(code, lo):
    op = ins.op_str
    if ins.mnemonic == "mov" and op.startswith(("eax", "ebx", "ecx", "edx", "esi", "edi")) \
            and "dword ptr [" in op and "+" in op:
        try:
            dst, src = op.split(",", 1)
            disp = int(src.split("+")[1].split("]")[0].strip(), 16)
            recent[dst.strip()] = (ins.address, disp)
        except Exception:
            pass
    if ins.mnemonic == "call" and op in ("eax", "ebx", "ecx", "edx", "esi", "edi"):
        r = op
        if r in recent and ins.address - recent[r][0] < 40:
            va0, disp = recent[r]
            if flt is None or disp == flt:
                n += 1
                print("0x%08X call %-3s <= [..+0x%x] @0x%08X" % (ins.address, r, disp, va0))
print("TOTAL", n)
