# -*- coding: utf-8 -*-
"""016: resync-disassemble [lo,hi) and report instructions referencing [reg+disp]."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _015_lib import BASE, DATA, MD
from capstone.x86 import X86_OP_MEM

lo = int(sys.argv[1], 16); hi = int(sys.argv[2], 16)
disps = [int(x, 16) for x in sys.argv[3].split(",")]
only_w = "--w" in sys.argv

pos = lo
while pos < hi:
    code = DATA[pos - BASE: min(hi - BASE, pos - BASE + 16)]
    ins = next(MD.disasm(code, pos), None)
    if ins is None or ins.size == 0 or pos + ins.size > hi:
        pos += 1
        continue
    for op in ins.operands:
        if op.type != X86_OP_MEM:
            continue
        m = op.mem
        if m.disp in disps and m.index == 0:
            isw = (ins.operands[0].type == X86_OP_MEM)
            if only_w and not isw:
                break
            base = ins.reg_name(m.base) if m.base else "?"
            print("0x%08X  [%s] %-22s %-30s  base=%s disp=0x%X"
                  % (ins.address, "W" if isw else "r", ins.bytes.hex(),
                     ins.mnemonic + " " + ins.op_str, base, m.disp))
            break
    pos += ins.size
