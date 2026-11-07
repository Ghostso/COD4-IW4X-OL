# EX-062 TASK E/J: find every vtable-dispatch site in iips.dll that could
# reach InitInGameApp (slot +0x50 of the CNIFS primary vtable 0x1003530C),
# plus every other reference to 0x9860 (function pointer publication).
import csv
import json
from collections import OrderedDict, defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow

INIT_INGAME = 0x9860


def main():
    img = Image(DLL)
    base = img.base
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("J-1  every 4-byte little-endian occurrence of 0x10009860 in iips.dll")
    print("=" * 78)
    raw = open(DLL, "rb").read()
    needle = (base + INIT_INGAME).to_bytes(4, "little")
    offs = []
    st = 0
    while True:
        i = raw.find(needle, st)
        if i < 0:
            break
        offs.append(i)
        st = i + 1
    print("   count = %d" % len(offs))
    for o in offs:
        rva = None
        secn = None
        for s in img.sections:
            if s["raw"] <= o < s["raw"] + s["rawsize"]:
                rva = s["va"] + (o - s["raw"])
                secn = s["name"]
                break
        print("      raw 0x%06X  RVA 0x%06X  VA 0x%08X  section %s" % (
            o, rva if rva else 0, base + rva if rva else 0, secn))
        if rva is not None:
            # is it inside the vtable?
            if 0x3530C <= rva < 0x3530C + 54 * 4:
                slot = (rva - 0x3530C) // 4
                print("           ==> CNIFS primary vtable 0x1003530C "
                      "slot %d (+0x%X)" % (slot, slot * 4))

    print()
    print("=" * 78)
    print("J-2  immediate CALL 0x10009860")
    print("=" * 78)
    entries = sorted(find_entries(img))
    calls = []
    for c in entries:
        b = grow(img, c, md)
        for rva, i in b.items():
            if i.mnemonic == "call" and i.operands \
                    and i.operands[0].type == X86_OP_IMM \
                    and i.operands[0].imm - base == INIT_INGAME:
                calls.append((c, rva))
    print("   count = %d" % len(set(calls)))

    print()
    print("=" * 78)
    print("J-3  arithmetic vtable dispatch pattern:  [obj] -> [vt+0x50] -> call")
    print("=" * 78)
    print("   pattern: mov reg,[obj]  ; mov reg2,[reg+0x50] ; call reg2")
    hits = []
    for c in entries:
        b = grow(img, c, md)
        rvas = sorted(b)
        for idx, rva in enumerate(rvas):
            i = b[rva]
            if i.mnemonic != "mov" or len(i.operands) != 2:
                continue
            d, s = i.operands
            # look for: mov r, [r2 + 0x50]  (vtable slot fetch)
            if d.type == X86_OP_REG and s.type == X86_OP_MEM \
                    and s.mem.disp == 0x50 and s.mem.base != 0:
                # find a nearby call through the same register
                reg = md.reg_name(d.reg)
                for r2 in rvas[idx + 1: idx + 6]:
                    j = b[r2]
                    if j.mnemonic == "call" and j.operands \
                            and j.operands[0].type == X86_OP_REG \
                            and md.reg_name(j.operands[0].reg) == reg:
                        hits.append((c, rva, r2, reg))
                        break
    print("   count = %d" % len(hits))
    for c, rva, r2, reg in hits:
        print("      owner sub_%X : 0x%X mov %s,[..+0x50]  ... 0x%X call %s"
              % (c, rva, reg, r2, reg))

    print()
    print("=" * 78)
    print("J-4  ALL dispatch sites using slot +0x50, ANY base register form")
    print("=" * 78)
    all050 = []
    for c in entries:
        b = grow(img, c, md)
        for rva, i in b.items():
            for op in i.operands:
                if op.type == X86_OP_MEM and op.mem.disp == 0x50:
                    all050.append((c, rva, "%s %s" % (i.mnemonic, i.op_str)))
    uniq = OrderedDict()
    for c, rva, t in all050:
        uniq[(rva, t)] = c
    print("   total instructions with [..+0x50]: %d" % len(uniq))
    for (rva, t), c in sorted(uniq.items()):
        print("      sub_%-8X 0x%05X  %s" % (c, rva, t))


if __name__ == "__main__":
    main()
