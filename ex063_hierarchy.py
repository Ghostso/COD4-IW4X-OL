# EX-063 TASK C/B: map the manager class hierarchy (all vtables written by
# the two constructors) and their slot maps.
import csv
import json
from collections import OrderedDict

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow

import capstone as cs


def walk_vt(img, va, limit=256):
    base = img.base
    rva = va - base
    s = rva
    while s - 4 >= 0x33000:
        v = int.from_bytes(img.read(s - 4, 4), "little")
        if not (base <= v < base + img.size) or not img.is_code(v - base):
            break
        s -= 4
    out = []
    for n in range(limit):
        sr = s + n * 4
        v = int.from_bytes(img.read(sr, 4), "little")
        if not (base <= v < base + img.size):
            break
        t = v - base
        if not img.is_code(t):
            break
        out.append((n, sr, v, t))
    return s, out


def main():
    img = Image(DLL)
    base = img.base
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    vts = [0x1003929C, 0x1003926C, 0x100344E4, 0x10039290,
           0x1003934C, 0x1003940C, 0x10039430, 0x10039438,
           0x10035660]

    print("=" * 78)
    print("manager class hierarchy: all vtable immediates written by")
    print("the two constructors sub_11F20 and sub_124D0")
    print("=" * 78)

    rows = []
    for va in vts:
        start, slots = walk_vt(img, va)
        print()
        print("-- vtable VA 0x%X  (start RVA 0x%X)  slots=%d" % (
            va, start, len(slots)))
        for n, sr, v, t in slots[:60]:
            mark = ""
            if t == 0x197F0:
                mark = "   <<<<<< sub_197F0"
            print("     slot %-3d +0x%02X  0x%05X -> 0x%08X (sub_%X)%s" % (
                n, n * 4, sr, v, t, mark))
            rows.append(["0x%X" % va, "0x%X" % start, n, "0x%X" % (n * 4),
                         "0x%X" % sr, "0x%X" % v, "0x%X" % t,
                         "sub_%X" % t])
        if not slots:
            print("     (not a code-pointer table)")

    with open("ex063_manager_vtable_all.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vtable_va", "vtable_start_rva", "slot", "slot_offset",
                    "slot_rva", "slot_value", "target_rva", "target_fn"])
        w.writerows(rows)
    print()
    print("wrote ex063_manager_vtable_all.csv (%d rows)" % len(rows))

    print()
    print("=" * 78)
    print("constructor vtable-write sequences (chronological)")
    print("=" * 78)
    for entry, name in ((0x11F20, "sub_11F20"), (0x124D0, "sub_124D0")):
        b = grow(img, entry, md)
        print()
        print("-- %s (0x%X)" % (name, entry))
        for rva in sorted(b):
            i = b[rva]
            for op in i.operands:
                if op.type == 2 and 0x10030000 <= op.imm < 0x10042000:
                    print("     0x%05X  %s %s" % (rva, i.mnemonic, i.op_str))


if __name__ == "__main__":
    main()
