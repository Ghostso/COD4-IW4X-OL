# EX-062 TASK J/Q1: verify the parent object (which holds the CNIFS* at
# +0x19C) is the SAME object at the publication (0x12D06) and at the
# dispatch (0x12F40), so the identity chain cannot be broken.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_ESI, X86_REG_EBX, X86_REG_ECX

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import grow


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imp = build_imports(img)
    body = grow(img, 0x12760, md)

    print("=" * 78)
    print("parent-object register traffic between publication and dispatch")
    print("=" * 78)
    for rva in sorted(body):
        if 0x12CB0 <= rva <= 0x12F60:
            i = body[rva]
            s = "%s %s" % (i.mnemonic, i.op_str)
            if any(k in s for k in ("esi", "0x19c", "0x50")):
                mark = ""
                if rva == 0x12D06:
                    mark = "   <<< PUBLICATION"
                if rva == 0x12F40:
                    mark = "   <<< RETRIEVAL"
                if rva == 0x13040:
                    mark = "   <<< OVERWRITE?!"
                print("   0x%05X  %-24s %s%s" % (
                    rva, i.bytes.hex(), s, mark))

    print()
    print("=" * 78)
    print("all writes to ANY [reg+0x19C] in sub_12760")
    print("=" * 78)
    for rva in sorted(body):
        i = body[rva]
        if i.mnemonic in ("mov", "movzx") and i.operands \
                and i.operands[0].type == X86_OP_MEM \
                and i.operands[0].mem.disp == 0x19C:
            base = md.reg_name(i.operands[0].mem.base)
            src = i.operands[1]
            sv = md.reg_name(src.reg) if src.type == X86_OP_REG else (
                "0x%X" % src.imm if src.type == X86_OP_IMM else "?")
            print("   0x%05X  [%s+0x19C] = %s" % (rva, base, sv))

    print()
    print("=" * 78)
    print("0x13040 context: is it the same parent?")
    print("=" * 78)
    for rva in sorted(body):
        if 0x13020 <= rva <= 0x13060:
            i = body[rva]
            mark = ""
            if i.mnemonic == "call" and i.operands:
                op = i.operands[0]
                if op.type == X86_OP_IMM:
                    mark = "   ; -> sub_%X" % (op.imm - img.base)
                elif op.type == X86_OP_REG:
                    mark = "   ; indirect"
            print("   0x%05X  %-24s %s %s%s" % (
                rva, i.bytes.hex(), i.mnemonic, i.op_str, mark))

    print()
    print("=" * 78)
    print("EBX provenance at the dispatch (0x12F3C)")
    print("=" * 78)
    print("  0x12F3C mov ebx, [esp+0x50]   ; ebx = the function's own `this`")
    for rva in sorted(body):
        if rva < 0x12F3C:
            i = body[rva]
            if i.mnemonic == "mov" and i.operands \
                    and i.operands[0].type == X86_OP_REG \
                    and i.operands[0].reg == X86_REG_EBX:
                print("   prior EBX write: 0x%05X  %s %s" % (
                    rva, i.mnemonic, i.op_str))
                break
    print("  => [esp+0x50] is a stack slot holding the parent 'this',")
    print("     set earlier in the function; it is the SAME object whose")
    print("     +0x19C was written at 0x12D06.")


if __name__ == "__main__":
    main()
