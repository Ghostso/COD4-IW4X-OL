#!/usr/bin/env python3
"""138: detect 'mov regA,[regB+disp]; ...; call regA' vtable-forwarder sequences.
usage: s138_fwd.py <lo> <hi> [disp_filter_hex]
Prints each indirect call through a register that was loaded from [reg+disp]
within the previous few instructions.
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
flt = int(sys.argv[3], 0) if len(sys.argv) > 3 else None

code = d[lo - VA:hi - VA]
recent = {}  # reg -> (va, disp)
hist = []
for ins in md.disasm(code, lo):
    op = ins.op_str
    # track 'mov reg, dword ptr [reg2 + disp]'
    if ins.mnemonic == "mov" and "dword ptr [" in op and "+" in op:
        try:
            dst, src = op.split(",", 1)
        except ValueError:
            dst, src = "", ""
        dst = dst.strip()
        if "[" in src:
            try:
                disp = int(src.split("+")[1].split("]")[0].strip(), 16)
            except Exception:
                disp = None
            if disp is not None and dst in ("eax", "ebx", "ecx", "edx", "esi", "edi"):
                recent[dst] = (ins.address, disp)
    # call reg
    if ins.mnemonic == "call" and op.strip() in ("eax", "ebx", "ecx", "edx", "esi", "edi"):
        r = op.strip()
        if r in recent:
            va0, disp = recent[r]
            if flt is None or disp == flt:
                print("0x%08X call %-3s <= mov %s,[..+0x%x] @0x%08X || %s" % (
                    ins.address, r, r, disp, va0, " ; ".join(hist[-5:])))
    hist.append("0x%08X %s %s" % (ins.address, ins.mnemonic, op))
