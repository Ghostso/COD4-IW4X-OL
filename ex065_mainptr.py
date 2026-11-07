# EX-065 PHASE 1: locate the CRT's application-entry pointer by scanning
# for the function-pointer table the modern MSVC CRT reads.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img

TCLS = r"WeGame\tcls\tcls_core.exe"


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("the CRT startup body: 0xB2847..0xB29AD full listing")
    print("=" * 78)
    r = 0xB2847
    n = 0
    while r <= 0xB29AD and n < 200:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            r += 1
            continue
        mark = ""
        if insn.mnemonic == "call" and insn.operands:
            op = insn.operands[0]
            if op.type == X86_OP_MEM and op.mem.base == 0:
                nm = img.imports.get(op.mem.disp - img.base)
                if nm:
                    mark = "   ; %s!%s" % nm
            elif op.type == X86_OP_MEM:
                mark = "   ; IND [%s+0x%X]" % (
                    md.reg_name(op.mem.base) if op.mem.base else "-",
                    op.mem.disp)
            elif op.type == X86_OP_REG:
                mark = "   ; IND %s" % md.reg_name(op.reg)
            elif op.type == X86_OP_IMM:
                mark = "   ; -> sub_%X" % (op.imm - img.base)
        print("   0x%05X  %-24s %s %s%s" % (
            r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
        r += insn.size
        n += 1

    print()
    print("=" * 78)
    print("0xB2093 and 0xB218E (called from the CRT before the app entry)")
    print("=" * 78)
    for entry in (0xB2093, 0xB218E, 0xB2CD0):
        print()
        print("-- sub_%X --" % entry)
        r = entry
        n = 0
        while n < 45:
            insn = next(md.disasm(img.read(r, 16), img.base + r), None)
            if insn is None:
                break
            mark = ""
            if insn.mnemonic == "call" and insn.operands:
                op = insn.operands[0]
                if op.type == X86_OP_IMM:
                    mark = "   ; -> sub_%X" % (op.imm - img.base)
                elif op.type == X86_OP_MEM and op.mem.base == 0:
                    nm = img.imports.get(op.mem.disp - img.base)
                    if nm:
                        mark = "   ; %s!%s" % nm
                elif op.type == X86_OP_MEM:
                    mark = "   ; IND [%s+0x%X]" % (
                        md.reg_name(op.mem.base) if op.mem.base else "-",
                        op.mem.disp)
            print("     0x%05X  %-22s %s %s%s" % (
                r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
            if insn.mnemonic.startswith("ret"):
                break
            r += insn.size
            n += 1


if __name__ == "__main__":
    main()
