# EX-063 TASK C: recover the manager object constructor(s) and publication.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow

VT_VA = 0x1003934C


def show(img, md, imp, entry, lo, hi, title):
    b = grow(img, entry, md)
    print("=" * 78)
    print(title)
    print("=" * 78)
    print("  entry 0x%05X  body 0x%05X..0x%05X  %d insns" % (
        entry, min(b), max(b), len(b)))
    for rva in sorted(b):
        if not (lo <= rva <= hi):
            continue
        i = b[rva]
        mark = ""
        if i.mnemonic == "call" and i.operands:
            op = i.operands[0]
            if op.type == X86_OP_IMM:
                mark = "   ; -> sub_%X" % (op.imm - img.base)
            elif op.type == X86_OP_MEM and op.mem.base == 0:
                n = imp.get(op.mem.disp - img.base)
                if n:
                    mark = "   ; %s!%s" % n
            elif op.type == X86_OP_MEM:
                mark = "   ; IND [%s+0x%X]" % (
                    md.reg_name(op.mem.base), op.mem.disp)
            elif op.type == X86_OP_REG:
                mark = "   ; IND %s" % md.reg_name(op.reg)
        print("    0x%05X  %-24s %s %s%s" % (
            rva, i.bytes.hex(), i.mnemonic, i.op_str, mark))
    return b


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imp = build_imports(img)

    # ctor candidate 1: owns 0x11FB1
    b1 = grow(img, 0x11F27, md)
    # ctor candidate 2: owns 0x124FB
    b2 = grow(img, 0x124D7, md)

    print("=" * 78)
    print("which function contains each vtable-install site?")
    print("=" * 78)
    for site in (0x11FB1, 0x124FB):
        owners = []
        for c in sorted(find_entries(img)):
            if site in grow(img, c, md):
                owners.append(c)
        print("  0x%05X owners: %s -> outermost sub_%X" % (
            site, ["0x%X" % o for o in sorted(owners)[:5]], min(owners)))

    show(img, md, imp, 0x11F27, 0x11F27, 0x11FE0,
         "MANAGER CTOR CANDIDATE 1 : sub_11F27  (installs vt at 0x11FB1)")
    print()
    show(img, md, imp, 0x124D7, 0x124D7, 0x12560,
         "MANAGER CTOR CANDIDATE 2 : sub_124D7  (installs vt at 0x124FB)")

    print()
    print("=" * 78)
    print("slot 0 target sub_12480 (the most-derived vtable's slot 0)")
    print("=" * 78)
    show(img, md, imp, 0x12480, 0x12480, 0x124D7,
         "sub_12480")


if __name__ == "__main__":
    main()
