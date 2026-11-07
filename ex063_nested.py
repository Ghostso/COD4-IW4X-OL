# EX-063 TASK F/H: determine whether the "manager" at [X+0x19C] (whose
# slot 1 is sub_197F0) is the SAME class instance chain as the one
# sub_12760 uses, or a nested different object.
import json
from collections import defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def fset(img, md, entry, reg):
    b = grow(img, entry, md)
    s = set()
    for i in b.values():
        for o in i.operands:
            if o.type == X86_OP_MEM and o.mem.base and o.mem.index == 0:
                if md.reg_name(o.mem.base) == reg:
                    s.add(o.mem.disp)
    return s


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("class A = the object sub_12760 uses as its `this` (EBX/ESI)")
    print("=" * 78)
    a = fset(img, md, 0x12760, "ebx") | fset(img, md, 0x12760, "esi")
    print("   fields: %s" % " ".join("+0x%X" % x for x in sorted(a)))

    print()
    print("class B = the object sub_1A270 uses (ESI = ecx)")
    print("=" * 78)
    b = fset(img, md, 0x1A270, "esi")
    print("   fields: %s" % " ".join("+0x%X" % x for x in sorted(b)))

    print()
    print("   B subset of A? %s" % b.issubset(a))
    print("   B - A: %s" % (" ".join("+0x%X" % x for x in sorted(b - a))
                            or "(none)"))
    print("   A - B: %s" % (" ".join("+0x%X" % x for x in sorted(a - b))
                            or "(none)"))

    print()
    print("=" * 78)
    print("which vtable do the [X+0x19C] readers dispatch to?")
    print("   [esi+0x19C] -> [ecx] -> [eax+SLOT] -> call")
    print("=" * 78)
    readers = [0x13900, 0x13A60, 0x13D60, 0x13E80, 0x14A00, 0x15EE0,
               0x16C50, 0x17920, 0x17F60, 0x181A0, 0x18300, 0x18520,
               0x19030, 0x19110, 0x191A0, 0x19220, 0x19BC0,
               0x1A1A0, 0x1A270, 0x1A410, 0x1A5B0, 0x1A760, 0x1A7E0,
               0x1A990, 0x1AC40, 0x1ACD0, 0x1AD60, 0x1ADE0]
    slots = defaultdict(list)
    for e in readers:
        bb = grow(img, e, md)
        rvas = sorted(bb)
        for idx, rva in enumerate(rvas):
            i = bb[rva]
            if i.mnemonic == "mov" and len(i.operands) == 2 \
                    and i.operands[0].type == X86_OP_REG \
                    and i.operands[1].type == X86_OP_MEM \
                    and i.operands[1].mem.disp == 0x19C:
                obj = md.reg_name(i.operands[0].reg)
                # find next [reg2] load and [reg2+slot]
                for r2 in rvas[idx + 1: idx + 8]:
                    j = bb[r2]
                    if j.mnemonic == "mov" and len(j.operands) == 2 \
                            and j.operands[0].type == X86_OP_REG \
                            and j.operands[1].type == X86_OP_MEM \
                            and j.operands[1].mem.base != 0 \
                            and j.operands[1].mem.disp == 0 \
                            and md.reg_name(j.operands[1].mem.base) == obj:
                        vt = md.reg_name(j.operands[0].reg)
                        for r3 in rvas[rvas.index(r2) + 1: rvas.index(r2) + 6]:
                            k = bb[r3]
                            if k.mnemonic == "mov" and len(k.operands) == 2 \
                                    and k.operands[0].type == X86_OP_REG \
                                    and k.operands[1].type == X86_OP_MEM \
                                    and md.reg_name(
                                        k.operands[1].mem.base) == vt:
                                slots[k.operands[1].mem.disp].append(
                                    (e, rva, k.mnemonic + " " + k.op_str))
                        break
    print("   slot offsets observed:")
    for s in sorted(slots):
        print("      +0x%02X : %d sites  e.g. %s" % (
            s, len(slots[s]), ["sub_%X@0x%X" % (e, r)
                               for e, r, _ in slots[s][:3]]))


if __name__ == "__main__":
    main()
