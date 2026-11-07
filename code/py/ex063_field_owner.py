# EX-063 TASK F: decide the class that owns the field +0x19C at
# sub_1A270+0x1A2FC, by comparing the full field profile of that object
# against the two known classes (CNIFS sizeof 0x1F0, manager sizeof ?).
import json
from collections import defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def profile(img, md, entry, base_regs):
    b = grow(img, entry, md)
    out = defaultdict(set)
    for rva in sorted(b):
        i = b[rva]
        for op in i.operands:
            if op.type == X86_OP_MEM and op.mem.base and op.mem.index == 0:
                r = md.reg_name(op.mem.base)
                if r in base_regs:
                    out[r].add(op.mem.disp)
    return b, out


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("class profiles")
    print("=" * 78)
    # CNIFS: this = ebp in initIfsLib / InitInGameApp
    cf = set()
    for e in (0x9570, 0x9860):
        _, p = profile(img, md, e, {"ebp"})
        cf |= p["ebp"]
    print("  CNIFS (this=ebp in 0x9570/0x9860): %d disps" % len(cf))
    print("     %s" % " ".join("+0x%X" % x for x in sorted(cf)))

    # manager ctor base sizes
    b1 = grow(img, 0x11F20, md)
    print()
    print("  manager ctor sub_11F20: %d insns, fields up to 0x%X" % (
        len(b1), max(
            (o.mem.disp for i in b1.values() for o in i.operands
             if o.type == X86_OP_MEM and o.mem.base
             and md.reg_name(o.mem.base) == "ebp"), default=0)))
    b2 = grow(img, 0x124D0, md)
    print("  manager ctor sub_124D0: %d insns, fields up to 0x%X" % (
        len(b2), max(
            (o.mem.disp for i in b2.values() for o in i.operands
             if o.type == X86_OP_MEM and o.mem.base
             and md.reg_name(o.mem.base) == "edi"), default=0)))

    print()
    print("=" * 78)
    print("the object at sub_1A270: esi = ecx (this)")
    print("=" * 78)
    b, p = profile(img, md, 0x1A270, {"esi", "ecx", "edi", "ebx"})
    print("  esi-field disps: %s" % " ".join(
        "+0x%X" % x for x in sorted(p["esi"])))
    print()
    print("  max esi disp: +0x%X" % max(p["esi"]))
    print("  does it fit in sizeof(CNIFS) = 0x1F0 ? %s" % (
        max(p["esi"]) < 0x1F0))
    print()
    print("  CNIFS profile overlap   : %s" % (
        " ".join("+0x%X" % x for x in sorted(set(p["esi"]) & cf))))
    print("  NON-CNIFS disps         : %s" % (
        " ".join("+0x%X" % x for x in sorted(set(p["esi"]) - cf))))


if __name__ == "__main__":
    main()
