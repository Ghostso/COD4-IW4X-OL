# EX-063 TASK D/G: precise search for a dispatch of vtable slot +0x04 on an
# object obtained from a parent field, especially +0x19C (the parent slot
# that sub_12760 writes the CNIFS* into).
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def main():
    img = Image(DLL)
    base = img.base
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    entries = sorted(find_entries(img))
    cache = {}
    owner = {}
    for c in entries:
        b = grow(img, c, md)
        cache[c] = b
        for rva in b:
            if rva not in owner or c < owner[rva]:
                owner[rva] = c

    print("=" * 78)
    print("A) reads of [X+0x19C] followed by an indirect call through [Y+0x04]")
    print("   within a short window (the 'CNIFS slot-1' hypothesis)")
    print("=" * 78)
    hits = []
    for rva in sorted(owner):
        i = cache[owner[rva]][rva]
        for o in i.operands:
            if o.type == X86_OP_MEM and o.mem.disp == 0x19C:
                own = owner[rva]
                b = cache[own]
                window = [x for x in sorted(b) if rva < x <= rva + 0x80]
                found = []
                for x in window:
                    j = b[x]
                    if j.mnemonic == "call" and j.operands \
                            and j.operands[0].type == X86_OP_REG:
                        found.append((x, md.reg_name(j.operands[0].reg)))
                if found:
                    hits.append((own, rva, "%s %s" % (i.mnemonic, i.op_str),
                                 found))
    print("   count = %d" % len(hits))
    for own, rva, text, found in hits:
        print("      sub_%-8X 0x%05X  %s" % (own, rva, text))
        for x, reg in found[:4]:
            print("             -> call %s at 0x%05X" % (reg, x))

    print()
    print("=" * 78)
    print("B) the [obj+0x19C] + slot +0x04 pattern: full block dump")
    print("=" * 78)
    for own, rva, text, found in hits:
        print()
        print("   --- sub_%X @ 0x%05X ---" % (own, rva))
        b = cache[own]
        lo = rva - 0x20
        hi = found[0][0] + 0x10
        for x in sorted(y for y in b if lo <= y <= hi):
            j = b[x]
            mark = ""
            if x == rva:
                mark = "   <<< 0x19C read"
            if x in [f[0] for f in found]:
                mark = "   <<< indirect call"
            print("      0x%05X  %-22s %s %s%s" % (
                x, j.bytes.hex(), j.mnemonic, j.op_str, mark))

    print()
    print("=" * 78)
    print("C) ALL sites where [reg+4] is fetched AND the object came from")
    print("   a [parent+0x19C]-like field (search all 0x1xx disps)")
    print("=" * 78)
    # For each indirect call through a fetched slot, trace back the object reg
    return


if __name__ == "__main__":
    main()
