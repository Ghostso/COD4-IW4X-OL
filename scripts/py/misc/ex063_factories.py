# EX-063 TASK G/J: recover iips.dll's exported factory functions and see
# whether they construct and return the manager object (which would be the
# external entry point).
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def main():
    img = Image(DLL)
    base = img.base
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imp = build_imports(img)

    print("=" * 78)
    print("iips.dll exports")
    print("=" * 78)
    exps = []
    for e in img.pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if e.name:
            exps.append((e.name.decode(), e.address))
            print("   %-28s RVA 0x%X" % (e.name.decode(), e.address))

    print()
    print("=" * 78)
    print("bodies of the exported factories")
    print("=" * 78)
    for name, rva in exps:
        print()
        print("-- %s (0x%X)" % (name, rva))
        b = grow(img, rva, md)
        print("   body 0x%X..0x%X  %d insns" % (min(b), max(b), len(b)))
        for r in sorted(b)[:40]:
            i = b[r]
            mark = ""
            if i.mnemonic == "call" and i.operands:
                op = i.operands[0]
                if op.type == X86_OP_IMM:
                    mark = "   ; -> sub_%X" % (op.imm - base)
                elif op.type == X86_OP_MEM and op.mem.base == 0:
                    n = imp.get(op.mem.disp - base)
                    mark = "   ; %s" % (n,)
                elif op.type == X86_OP_REG:
                    mark = "   ; IND %s" % md.reg_name(op.reg)
            print("     0x%05X  %-22s %s %s%s" % (
                r, i.bytes.hex(), i.mnemonic, i.op_str, mark))

    print()
    print("=" * 78)
    print("does any export reach the manager ctor sub_11F20 / sub_124D0?")
    print("=" * 78)
    entries = sorted(find_entries(img))
    for target, tname in ((0x11F20, "sub_11F20"), (0x124D0, "sub_124D0"),
                          (0x197F0, "sub_197F0"), (0x12760, "sub_12760")):
        hits = []
        for c in entries:
            bb = grow(img, c, md)
            for rva, i in bb.items():
                if i.mnemonic == "call" and i.operands \
                        and i.operands[0].type == X86_OP_IMM \
                        and i.operands[0].imm - base == target:
                    hits.append((c, rva))
        uniq = sorted(set(hits))
        print("   %-12s (0x%X): %d immediate callers  %s" % (
            tname, target, len(uniq),
            ["sub_%X@0x%X" % (c, r) for c, r in uniq[:8]]))


if __name__ == "__main__":
    main()
