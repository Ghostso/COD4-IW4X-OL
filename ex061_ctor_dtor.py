# EX-061 TASK 4/5: confirm CNIFS constructor and destructor, and pin down
# the initial value of [this+0x60].
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_EBX, X86_REG_ESI, X86_REG_EBP

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import grow


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imports = build_imports(img)

    print("=" * 78)
    print("CNIFS constructor candidate sub_90D0 (0x90D0)")
    print("=" * 78)
    body = grow(img, 0x90D0, md)
    print("  this source : 0x90F4  mov ebp, [esp+0x24]  (stack arg 1)")
    print("  ret         : 0x9214  ret 4                (pops 1 stack arg)")
    print("  return value: 0x91FF  mov eax, ebp         (returns this)")
    print()
    print("  zeroing register setup:")
    for rva in (0x90FF,):
        i = body[rva]
        print("    0x%05X  %-20s %s %s" % (rva, i.bytes.hex(), i.mnemonic, i.op_str))
    print()
    print("  member initialisation writes:")
    for rva in sorted(body):
        i = body[rva]
        if i.mnemonic == "mov" and i.operands and i.operands[0].type == X86_OP_MEM:
            base = md.reg_name(i.operands[0].mem.base)
            if base == "ebp":
                d = i.operands[0].mem.disp
                if d in (0x54, 0x58, 0x5C, 0x60, 0xCC, 0xF8, 0xFC, 0x100,
                         0x138, 0x144, 0x148, 0x14C, 0x150, 0x154, 0x155):
                    src = ""
                    if len(i.operands) > 1:
                        o = i.operands[1]
                        if o.type == X86_OP_REG:
                            src = md.reg_name(o.reg)
                        elif o.type == X86_OP_IMM:
                            src = "0x%X" % o.imm
                    print("    0x%05X  %-20s [this+0x%03X] = %s" % (
                        rva, i.bytes.hex(), d, src))

    print()
    print("=" * 78)
    print("CNIFS destructor candidate sub_9240 (0x9240)")
    print("=" * 78)
    body2 = grow(img, 0x9240, md)
    print("  this source : 0x9267  mov esi, ecx          (thiscall)")
    print("  ret         : 0x937F  ret                    (__thiscall, callee pops)")
    print()
    print("  +0x60 / +0x5C / +0x54 teardown:")
    for rva in sorted(body2):
        if 0x9293 <= rva <= 0x92E8:
            i = body2[rva]
            mark = ""
            if i.mnemonic == "call" and i.operands:
                op = i.operands[0]
                if op.type == X86_OP_MEM and op.mem.base == 0:
                    nm = imports.get(op.mem.disp - img.base)
                    if nm:
                        mark = "   ; %s!%s" % nm
            print("    0x%05X  %-22s %s %s%s" % (
                rva, i.bytes.hex(), i.mnemonic, i.op_str, mark))

    print()
    print("=" * 78)
    print("vtable constants installed by the constructor")
    print("=" * 78)
    for rva in sorted(body):
        i = body[rva]
        if i.mnemonic == "mov" and i.operands and i.operands[0].type == X86_OP_MEM:
            for o in i.operands[1:]:
                if o.type == X86_OP_IMM and 0x10030000 <= o.imm < 0x10042000:
                    d = i.operands[0].mem.disp
                    base = md.reg_name(i.operands[0].mem.base)
                    print("    0x%05X  [%s+0x%X] = 0x%X" % (
                        rva, base, d, o.imm))


if __name__ == "__main__":
    main()
