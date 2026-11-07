# EX-061: check whether [ebp+0x60] accesses in InitInGameApp belong to the
# CNIFS `this` pointer or to a DIFFERENT object stored in ebp later.
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_EBP

from ex060_iips_cfg import Image, DLL
from ex061_revalidate import grow


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    body = grow(img, 0x9860, md)

    print("=== every write to EBP in CNIFS::InitInGameApp ===")
    writes = []
    for rva in sorted(body):
        insn = body[rva]
        if len(insn.operands) >= 1 and insn.operands[0].type == X86_OP_REG \
                and insn.operands[0].reg == X86_REG_EBP:
            writes.append((rva, insn))
            print("  0x%05X  %-24s %s %s" % (
                rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))

    print()
    print("=== classification of the 4 [ebp+0x60] sites vs EBP writes ===")
    for s in (0x9A2B, 0x9B51, 0x9B66, 0x9B7B):
        wr = [w for w in writes if w[0] < s]
        last = max(wr, key=lambda x: x[0]) if wr else None
        print("  +0x%05X : last EBP write before = 0x%05X  (%s %s)" % (
            s, last[0] if last else 0,
            last[1].mnemonic if last else "-",
            last[1].op_str if last else "-"))

    print()
    print("=== disassembly 0x9B40..0x9B95 (EBP-shadow region) ===")
    for rva in sorted(body):
        if 0x9B40 <= rva <= 0x9B95:
            insn = body[rva]
            mark = ""
            if insn.operands and insn.operands[0].type == X86_OP_REG \
                    and insn.operands[0].reg == X86_REG_EBP:
                mark = "   <<< EBP OVERWRITTEN"
            print("  0x%05X  %-24s %s %s%s" % (
                rva, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))

    print()
    print("=== disassembly 0x9A20..0x9A60 (the 0x9A2B site) ===")
    for rva in sorted(body):
        if 0x9A20 <= rva <= 0x9A60:
            insn = body[rva]
            print("  0x%05X  %-24s %s %s" % (
                rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))


if __name__ == "__main__":
    main()
