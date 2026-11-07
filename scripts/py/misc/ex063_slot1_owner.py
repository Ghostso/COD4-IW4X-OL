# EX-063 TASK D/F/G: pin down the object at sub_1A26E+0x1A2FC and who
# reaches sub_1A26E.
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
    entries = sorted(find_entries(img))

    print("=" * 78)
    print("sub_1A26E prologue: where does ESI come from?")
    print("=" * 78)
    b = grow(img, 0x1A26E, md)
    print("  body 0x%05X..0x%05X  %d insns" % (min(b), max(b), len(b)))
    for rva in sorted(b):
        if 0x1A26E <= rva <= 0x1A2A0:
            i = b[rva]
            mark = ""
            if i.mnemonic == "call" and i.operands:
                op = i.operands[0]
                if op.type == X86_OP_IMM:
                    mark = "   ; -> sub_%X" % (op.imm - base)
                elif op.type == X86_OP_MEM and op.mem.base == 0:
                    mark = "   ; %s" % (imp.get(op.mem.disp - base),)
            print("    0x%05X  %-22s %s %s%s" % (
                rva, i.bytes.hex(), i.mnemonic, i.op_str, mark))

    print()
    print("=" * 78)
    print("callers of sub_1A26E (immediate + vtable slot membership)")
    print("=" * 78)
    hits = []
    for c in entries:
        bb = grow(img, c, md)
        for rva, i in bb.items():
            if i.mnemonic == "call" and i.operands \
                    and i.operands[0].type == X86_OP_IMM \
                    and i.operands[0].imm - base == 0x1A26E:
                hits.append((c, rva))
    print("   immediate callers: %d" % len(set(hits)))
    for c, r in sorted(set(hits)):
        print("      sub_%X at 0x%X" % (c, r))

    raw = open(DLL, "rb").read()
    needle = (base + 0x1A26E).to_bytes(4, "little")
    offs = []
    st = 0
    while True:
        i = raw.find(needle, st)
        if i < 0:
            break
        offs.append(i)
        st = i + 1
    print("   le32 occurrences of 0x1001A26E: %d" % len(offs))
    for o in offs:
        for s in img.sections:
            if s["raw"] <= o < s["raw"] + s["rawsize"]:
                rva = s["va"] + (o - s["raw"])
                tag = ""
                if 0x3934C <= rva < 0x3934C + 47 * 4:
                    slot = (rva - 0x3934C) // 4
                    tag = "   <== manager vtable 0x1003934C slot %d (+0x%X)" % (
                        slot, slot * 4)
                print("      raw 0x%06X RVA 0x%06X sec %s%s" % (
                    o, rva, s["name"], tag))
                break

    print()
    print("=" * 78)
    print("the manager vtable slots that RESOLVE to sub_1A26E / sub_197F0")
    print("=" * 78)
    for slot in range(47):
        va = 0x1003934C + slot * 4
        v = int.from_bytes(img.read(va - base, 4), "little")
        if v - base in (0x1A26E, 0x197F0, 0x1A410, 0x1A1A0, 0x1A5B0,
                        0x1A760, 0x1A7E0):
            print("   slot %-3d +0x%02X -> sub_%X" % (slot, slot * 4, v - base))


if __name__ == "__main__":
    main()
