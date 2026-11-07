# EX-061 TASK 1/2: exhaustive WRITE/READ/COMPARE/TEST/ADDRESS-TAKE table
# for the CNIFS field +0x60.
#
# Method: enumerate every [reg+0x60] instruction in .text (from
# ex061_this60_scan), attribute to a function, then classify the operation
# and the direction.
import csv
import json
from collections import OrderedDict, defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def classify(insn, md):
    """Return (kind, direction, detail) for an instruction touching +0x60."""
    m = insn.mnemonic
    ops = insn.operands
    mem = None
    for o in ops:
        if o.type == X86_OP_MEM and o.mem.disp == 0x60 and o.mem.index == 0:
            mem = o
            break
    if mem is None:
        return None
    dst_is_mem = (ops[0].type == X86_OP_MEM and ops[0].mem.disp == 0x60)
    if m == "cmp":
        return ("COMPARE", "READ", "%s %s" % (m, insn.op_str))
    if m == "test":
        return ("TEST", "READ", "%s %s" % (m, insn.op_str))
    if m == "lea":
        return ("ADDRESS_TAKE", "READ-NONE", "%s %s" % (m, insn.op_str))
    if m in ("mov", "movzx", "movsx", "movd"):
        if dst_is_mem:
            return ("WRITE", "WRITE", "%s %s" % (m, insn.op_str))
        return ("READ", "READ", "%s %s" % (m, insn.op_str))
    if m in ("add", "sub", "or", "and", "xor", "inc", "dec"):
        if dst_is_mem:
            return ("READ_MODIFY_WRITE", "WRITE", "%s %s" % (m, insn.op_str))
        return ("READ", "READ", "%s %s" % (m, insn.op_str))
    if m == "push":
        return ("CALL_ARGUMENT", "READ", "%s %s" % (m, insn.op_str))
    return ("OTHER", "?", "%s %s" % (m, insn.op_str))


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imports = build_imports(img)

    entries = sorted(find_entries(img))
    print("entries: %d" % len(entries))

    # Build union of decoded instructions with owner
    owner = {}
    body_cache = {}
    for c in entries:
        b = grow(img, c, md)
        body_cache[c] = b
        for rva in b:
            # first (largest) function that claims it wins; we then prefer
            # the OUTERMOST entry
            if rva not in owner or c < owner[rva]:
                owner[rva] = c

    print("owned instructions: %d" % len(owner))

    # Collect all +0x60 touches whose address is a valid decoded instruction
    rows = []
    for rva in sorted(owner):
        insn = body_cache[owner[rva]].get(rva)
        if insn is None:
            continue
        for o in insn.operands:
            if o.type == X86_OP_MEM and o.mem.disp == 0x60 and o.mem.index == 0:
                base = md.reg_name(o.mem.base) if o.mem.base else "abs"
                cl = classify(insn, md)
                if cl is None:
                    continue
                kind, direction, text = cl
                rows.append(dict(
                    site="0x%X" % rva,
                    owner="sub_%X" % owner[rva],
                    base=base,
                    accesses_this=(base in ("ebp", "esi", "edi", "ebx", "ecx")
                                   and owner[rva] in (
                                       0x9570, 0x9860, 0x90D0, 0x9240)),
                    kind=kind,
                    direction=direction,
                    insn="%s %s" % (insn.mnemonic, insn.op_str),
                ))

    print("total +0x60 touches on decoded instructions: %d" % len(rows))

    cnifs = [r for r in rows if r["owner"] in
             ("sub_9570", "sub_9860", "sub_90D0", "sub_9240")]
    print("CNIFS-family +0x60 touches: %d" % len(cnifs))
    print()
    print("=" * 78)
    print("CNIFS-family +0x60 operations (this == CNIFS)")
    print("=" * 78)
    hdr = "%-10s %-12s %-5s %-20s %s" % (
        "site", "owner", "base", "kind", "insn")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(cnifs, key=lambda x: int(x["site"], 16)):
        print("%-10s %-12s %-5s %-20s %s" % (
            r["site"], r["owner"], r["base"], r["kind"], r["insn"]))

    print()
    print("=" * 78)
    print("WRITE list (all owners)")
    print("=" * 78)
    for r in sorted([x for x in rows if x["kind"] == "WRITE"],
                    key=lambda x: int(x["site"], 16)):
        print("  %-10s %-12s base=%-5s %s" % (
            r["site"], r["owner"], r["base"], r["insn"]))

    with open("ex061_this60_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["site", "owner", "base",
                                          "accesses_this", "kind",
                                          "direction", "insn"])
        w.writeheader()
        for r in sorted(rows, key=lambda x: int(x["site"], 16)):
            w.writerow(r)
    print()
    print("wrote ex061_this60_table.csv (%d rows)" % len(rows))


if __name__ == "__main__":
    main()
