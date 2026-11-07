# EX-063 TASK F/Q1: identify the class of the sub_1A270-family objects
# (+0x5C/+0x60/+0x64/+0x19C/+0x34C) and check its vtable.
import json
from collections import defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def main():
    img = Image(DLL)
    base = img.base
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("the +0x34C family: all functions touching +0x34C")
    print("=" * 78)
    entries = sorted(find_entries(img))
    fam = {}
    for c in entries:
        b = grow(img, c, md)
        for rva, i in b.items():
            for o in i.operands:
                if o.type == X86_OP_MEM and o.mem.disp == 0x34C:
                    fam.setdefault(c, []).append((rva, i))
    print("   functions: %d" % len(fam))
    for c in sorted(fam):
        print("      sub_%-8X  %d sites" % (c, len(fam[c])))

    print()
    print("=" * 78)
    print("vtables installed by the +0x34C family (search ctor patterns)")
    print("=" * 78)
    # find any function that both writes a vtable immediate and touches +0x34C
    for c in sorted(fam):
        b = grow(img, c, md)
        for rva in sorted(b):
            i = b[rva]
            for o in i.operands:
                if o.type == X86_OP_IMM and 0x10030000 <= o.imm < 0x10042000:
                    print("      sub_%-8X 0x%05X  %s %s" % (
                        c, rva, i.mnemonic, i.op_str))

    print()
    print("=" * 78)
    print("who dispatches [X+0x19C] then [vt+4]: the sub_197F0 caller")
    print("=" * 78)
    for e, reg in ((0x1A270, "esi"),):
        b = grow(img, e, md)
        for rva in sorted(b):
            if 0x1A2FC <= rva <= 0x1A30B:
                i = b[rva]
                print("      0x%05X  %-22s %s %s" % (
                    rva, i.bytes.hex(), i.mnemonic, i.op_str))

    print()
    print("=" * 78)
    print("check: is sub_1A270 in the manager vtable 0x1003934C?")
    print("=" * 78)
    raw = open(DLL, "rb").read()
    for target in (0x1A270, 0x1A26E):
        n = (base + target).to_bytes(4, "little")
        cnt = raw.count(n)
        print("   0x%X occurrences: %d" % (target, cnt))

    print()
    print("   manager vtable 0x1003934C slots that are >= 0x1A000 and < 0x1B000:")
    for slot in range(47):
        va = 0x1003934C + slot * 4
        v = int.from_bytes(img.read(va - base, 4), "little") - base
        if 0x1A000 <= v < 0x1B000:
            print("      slot %-3d +0x%02X -> sub_%X" % (slot, slot * 4, v))


if __name__ == "__main__":
    main()
