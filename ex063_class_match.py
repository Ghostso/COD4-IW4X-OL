# EX-063 TASK F: is sub_1A270 the same class as the manager constructors?
# If yes, then [esi+0x19C] is that class's own field and holds CNIFS*,
# which would make the [vt+4] dispatch land in the CNIFS vtable, not in
# sub_197F0.  If different, there are two classes with a +0x19C field.
import json
from collections import defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def fields(img, md, entry, reg):
    b = grow(img, entry, md)
    out = set()
    for i in b.values():
        for o in i.operands:
            if o.type == X86_OP_MEM and o.mem.base and o.mem.index == 0:
                if md.reg_name(o.mem.base) == reg:
                    out.add(o.mem.disp)
    return b, out


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    # manager ctor this = ebp (sub_11F20) / edi (sub_124D0)
    _, mgr = fields(img, md, 0x11F20, "ebp")
    _, mgr2 = fields(img, md, 0x124D0, "edi")
    MGR = mgr | mgr2
    print("manager class field count: %d" % len(MGR))
    print("  sample: %s" % " ".join("+0x%X" % x for x in sorted(MGR)[:30]))

    # the dispatcher object
    _, disp = fields(img, md, 0x1A270, "esi")
    print()
    print("sub_1A270 this(esi) field count: %d" % len(disp))
    print("  fields: %s" % " ".join("+0x%X" % x for x in sorted(disp)))
    print("  all in manager class? %s" % disp.issubset(MGR))
    print("  not-in-manager: %s" % (
        " ".join("+0x%X" % x for x in sorted(disp - MGR)) or "(none)"))

    print()
    print("=" * 78)
    print("the other [X+0x19C] readers: what is their `this` class?")
    print("=" * 78)
    readers = [
        (0x13900, "esi"), (0x13A60, "edi"), (0x13D60, "esi"),
        (0x13E80, "edi"), (0x14730, "ebx"), (0x14A00, "edi"),
        (0x15EE0, "esi"), (0x16C50, "esi"), (0x17920, "ebx"),
        (0x17F60, "edi"), (0x181A0, "esi"), (0x18300, "edi"),
        (0x18520, "edi"), (0x19030, "esi"), (0x1A1A0, "esi"),
        (0x1A270, "esi"), (0x1A410, "esi"), (0x1A5B0, "esi"),
        (0x1A7E0, "esi"),
    ]
    print("   func      this-reg  fields  max     in-manager-class?")
    for e, reg in readers:
        _, f = fields(img, md, e, reg)
        if not f:
            print("   0x%-6X  %-8s  (none)" % (e, reg))
            continue
        print("   0x%-6X  %-8s  %-6d  +0x%-5X %s" % (
            e, reg, len(f), max(f), f.issubset(MGR)))


if __name__ == "__main__":
    main()
