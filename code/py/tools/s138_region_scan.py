#!/usr/bin/env python3
"""s138_region_scan: disassemble a VA range linearly, print instructions whose
memory operand has a given disp (any width) or whose op_str references reg+0x20/0x24.
Usage: python -I tools/s138_region_scan.py <loVA> <hiVA> [disp...]
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def hit_disp(ins, want):
    for op in ins.operands:
        if op.type != 3:      # X86_OP_MEM
            continue
        m = op.mem
        eff = m.disp
        if m.base in (4,) and m.index:   # SIB: disp counts once
            pass
        if want == 0x7C and eff == 0x7C:
            return True
        if eff == want:
            return True
    return False


def refs_20(ins):
    import re
    return bool(re.search(r"\+ 0x2[04]\]", ins.op_str))


lo = int(sys.argv[1], 0) - VA
hi = int(sys.argv[2], 0) - VA
disps = [int(x, 0) for x in sys.argv[3:]] or [0x20, 0x24]
code = d[lo:hi]
for ins in md.disasm(code, lo + VA):
    if not ins.operands:
        continue
    if any(hit_disp(ins, w) for w in disps):
        print("  0x%08X  %-24s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
