# EX-063 TASK A/B: full-image scan for references to the manager vtable
# 0x1003934C (iips.dll) and complete slot map.
#
# Read-only offline static analysis. No patching, no dynamic execution.
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow

VT_VA = 0x1003934C


def main():
    img = Image(DLL)
    base = img.base
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imp = build_imports(img)
    raw = open(DLL, "rb").read()

    print("=" * 78)
    print("TASK A: all references to manager vtable VA 0x%X" % VT_VA)
    print("=" * 78)

    needle = VT_VA.to_bytes(4, "little")
    offs = []
    st = 0
    while True:
        i = raw.find(needle, st)
        if i < 0:
            break
        offs.append(i)
        st = i + 1
    print("  little-endian byte occurrences: %d" % len(offs))
    for o in offs:
        sec = None
        rva = None
        for s in img.sections:
            if s["raw"] <= o < s["raw"] + s["rawsize"]:
                sec = s["name"]
                rva = s["va"] + (o - s["raw"])
                break
        print("     raw 0x%06X  RVA 0x%06X  VA 0x%08X  section %s" % (
            o, rva if rva is not None else 0,
            base + rva if rva is not None else 0, sec))

    print()
    print("  RVA-only encoding (imm32 = 0x3934C) occurrences:")
    rva_needle = (VT_VA - base).to_bytes(4, "little")
    offs2 = []
    st = 0
    while True:
        i = raw.find(rva_needle, st)
        if i < 0:
            break
        offs2.append(i)
        st = i + 1
    print("     count = %d" % len(offs2))
    for o in offs2:
        for s in img.sections:
            if s["raw"] <= o < s["raw"] + s["rawsize"]:
                rva = s["va"] + (o - s["raw"])
                print("     raw 0x%06X RVA 0x%06X VA 0x%08X sec %s" % (
                    o, rva, base + rva, s["name"]))
                break

    print()
    print("  instructions whose immediate/memory operand equals 0x%X:" % VT_VA)
    entries = sorted(find_entries(img))
    found = []
    for c in entries:
        b = grow(img, c, md)
        for rva, i in b.items():
            for op in i.operands:
                if op.type == X86_OP_IMM and op.imm == VT_VA:
                    found.append((c, rva, "%s %s" % (i.mnemonic, i.op_str)))
                elif op.type == X86_OP_MEM and op.mem.base == 0 \
                        and op.mem.disp == VT_VA:
                    found.append((c, rva, "%s %s" % (i.mnemonic, i.op_str)))
    uniq = OrderedDict()
    for c, rva, t in found:
        uniq[rva] = (c, t)
    print("     count = %d" % len(uniq))
    for rva in sorted(uniq):
        c, t = uniq[rva]
        print("     sub_%-8X 0x%05X  %s" % (c, rva, t))

    print()
    print("=" * 78)
    print("TASK B: manager vtable 0x%X slot map" % VT_VA)
    print("=" * 78)
    rva = VT_VA - base
    # walk backwards to true start
    s = rva
    while s - 4 >= 0x33000:
        v = int.from_bytes(img.read(s - 4, 4), "little")
        if not (base <= v < base + img.size) or not img.is_code(v - base):
            break
        s -= 4
    print("  vtable start RVA 0x%X  VA 0x%X" % (s, base + s))
    slots = []
    for n in range(0, 256):
        sr = s + n * 4
        v = int.from_bytes(img.read(sr, 4), "little")
        if not (base <= v < base + img.size):
            break
        t = v - base
        if not img.is_code(t):
            break
        slots.append((n, sr, v, t))
    print("  total slots: %d  size 0x%X" % (len(slots), len(slots) * 4))
    print()
    print("  slot  off   slot_rva  slot_value   target_rva")
    for n, sr, v, t in slots:
        mark = ""
        if t == 0x197F0:
            mark = "   <<<<<< sub_197F0"
        print("  %-4d  +0x%02X  0x%05X   0x%08X   0x%06X%s" % (
            n, n * 4, sr, v, t, mark))

    with open("ex063_manager_vtable.csv", "w", newline="",
              encoding="utf-8") as f:
        import csv
        w = csv.writer(f)
        w.writerow(["vtable_va", "vtable_rva", "slot", "slot_offset",
                    "slot_rva", "slot_value", "target_rva", "target_va",
                    "note"])
        for n, sr, v, t in slots:
            w.writerow(["0x%X" % VT_VA, "0x%X" % s, n, "0x%X" % (n * 4),
                        "0x%X" % sr, "0x%X" % v, "0x%X" % (base + t),
                        "0x%X" % t,
                        "sub_197F0" if t == 0x197F0 else ""])
    print()
    print("wrote ex063_manager_vtable.csv (%d slots)" % len(slots))


if __name__ == "__main__":
    main()
