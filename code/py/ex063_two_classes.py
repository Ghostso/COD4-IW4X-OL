# EX-063 TASK F/Q1-Q4: resolve whether [X+0x19C] is ONE field of ONE class
# or two different fields of two different classes.
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
    print("Who writes [X+0x19C] and what class is X?")
    print("=" * 78)
    writers = {
        0x12D06: ("sub_12760", "CNIFS* from ctor",
                  "parent up to at least +0x2D4 (EX-062)"),
        0x13040: ("sub_12760", "0 (clear)", "same"),
        0x122AC: ("sub_11F27", "[ebp+0x19C] = ebx", "manager ctor"),
        0x137AB: ("sub_1375E", "[ebp+0x19C] = ebx", "manager method"),
    }
    for rva in sorted(writers):
        fn, what, note = writers[rva]
        print("   0x%05X  %-12s %-24s %s" % (rva, fn, what, note))

    print()
    print("=" * 78)
    print("the manager constructors' field maxima")
    print("=" * 78)
    for entry, base_reg in ((0x11F20, "ebp"), (0x124D0, "edi")):
        b = grow(img, entry, md)
        disps = [o.mem.disp for i in b.values() for o in i.operands
                 if o.type == X86_OP_MEM and o.mem.base
                 and md.reg_name(o.mem.base) == base_reg]
        print("   sub_%-8X max +0x%X   (fields >= 0x180: %s)" % (
            entry, max(disps),
            " ".join("+0x%X" % x for x in sorted(set(disps)) if x >= 0x180)))

    print()
    print("=" * 78)
    print("class of X in sub_12760 (the parent whose +0x19C gets the CNIFS*)")
    print("=" * 78)
    b = grow(img, 0x12760, md)
    disps = sorted(set(
        o.mem.disp for i in b.values() for o in i.operands
        if o.type == X86_OP_MEM and o.mem.base
        and md.reg_name(o.mem.base) in ("ebx", "esi")))
    print("   parent-object field disps (ebx/esi): %d" % len(disps))
    print("   max: +0x%X" % max(disps))
    print("   subset >= 0x180: %s" % " ".join(
        "+0x%X" % x for x in disps if x >= 0x180))

    print()
    print("   manager ctor covers up to +0x40C and +0x310;")
    print("   the parent in sub_12760 reaches up to +0x%X" % max(disps))

    print()
    print("=" * 78)
    print("VERDICT on [X+0x19C]")
    print("=" * 78)
    print("""
  sub_11F20 (manager ctor) writes [ebp+0x19C] = ebx (0).
  sub_12760 writes [esi+0x19C] = edi (the CNIFS* from sub_90D0).
  sub_1375E writes [ebp+0x19C] = ebx.
  sub_1A270 reads [esi+0x19C] and dispatches [vt+4] = sub_197F0.

  The object X in sub_12760 spans fields up to +0x2D4 (it also touches
  +0x23C, +0x240, +0x2D0, +0x2D4), so X is NOT a 0x1F0-sized CNIFS.
  The object at sub_1A270 spans up to +0x34C, also not CNIFS.

  => [X+0x19C] is a field of the SAME LARGE MANAGER-CLASS FAMILY used
     throughout iips.dll, and in sub_12760 that field is (re)assigned to
     the freshly constructed CNIFS*.

  => sub_1A270's `[esi+0x19C]` therefore holds whatever the manager
     stored there.  In sub_12760 that is the CNIFS*.  In sub_11F20 it is
     initialised to 0.

  CRITICAL: if sub_1A270's `esi` is the SAME manager instance whose
  +0x19C sub_12760 filled with the CNIFS*, then `[ecx]=CNIFS vtable
  0x1003530C` and `[eax+4] = 0x10007700`, NOT sub_197F0.

  A dispatch to sub_197F0 through [X+0x19C] therefore requires a
  DIFFERENT manager instance whose +0x19C holds ANOTHER MANAGER
  (a manager containing a manager).
""")


if __name__ == "__main__":
    main()
