# EX-063 TASK D/G: find every indirect dispatch through a vtable slot +0x04
# in iips.dll, and evaluate which could reach sub_197F0.
import json
from collections import OrderedDict

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
    print("TASK D: all [reg+0x04] vtable-slot FETCHES in iips.dll")
    print("=" * 78)
    entries = sorted(find_entries(img))
    body_cache = {}
    owner = {}
    for c in entries:
        b = grow(img, c, md)
        body_cache[c] = b
        for rva in b:
            if rva not in owner or c < owner[rva]:
                owner[rva] = c

    fetches = {}
    for rva in sorted(owner):
        i = body_cache[owner[rva]][rva]
        for oi, o in enumerate(i.operands):
            if o.type == X86_OP_MEM and o.mem.disp == 0x04 \
                    and o.mem.base != 0:
                dst = i.operands[0]
                if oi == 1 and dst.type == X86_OP_REG:
                    fetches[rva] = (owner[rva], md.reg_name(o.mem.base),
                                    md.reg_name(dst.reg),
                                    "%s %s" % (i.mnemonic, i.op_str))

    print("   total slot+0x04 fetches (mov reg,[base+4]): %d" % len(fetches))

    # For each fetch, look for a nearby indirect call through the same reg
    print()
    print("   fetch sites followed by a call through the fetched register:")
    hits = []
    for rva, (own, mbase, dst, text) in sorted(fetches.items()):
        b = body_cache[own]
        for r2 in sorted(x for x in b if rva < x <= rva + 0x40):
            j = b[r2]
            if j.mnemonic == "call" and j.operands:
                op = j.operands[0]
                if op.type == X86_OP_REG and md.reg_name(op.reg) == dst:
                    hits.append((own, rva, r2, mbase, dst, text))
                    break
    print("   count = %d" % len(hits))
    for own, rva, r2, mbase, dst, text in sorted(hits):
        print("      sub_%-8X fetch 0x%05X (%s, base=%s) -> call 0x%05X %s"
              % (own, rva, text, mbase, r2, dst))

    print()
    print("=" * 78)
    print("TASK D-2: the inverted form -- call dword ptr [reg+0x04]")
    print("=" * 78)
    tgt = []
    for rva in sorted(owner):
        i = body_cache[owner[rva]][rva]
        if i.mnemonic == "call" and i.operands:
            op = i.operands[0]
            if op.type == X86_OP_MEM and op.mem.disp == 0x04 \
                    and op.mem.base != 0:
                tgt.append((owner[rva], rva,
                            "call %s" % i.op_str))
    print("   count = %d" % len(tgt))
    for own, rva, t in sorted(tgt):
        print("      sub_%-8X 0x%05X  %s" % (own, rva, t))

    print()
    print("=" * 78)
    print("TASK G: does ANY site in iips.dll fetch [vt+0x04] where vt could")
    print("        be 0x1003934C?  Check the object source of each fetch.")
    print("=" * 78)
    for own, rva, r2, mbase, dst, text in sorted(hits):
        print()
        print("   --- fetch 0x%05X in sub_%X ---" % (rva, own))
        b = body_cache[own]
        lo = max(own, rva - 0x30)
        for x in sorted(y for y in b if lo <= y <= r2 + 4):
            i = b[x]
            mark = ""
            if x == rva:
                mark = "   <<< FETCH"
            if x == r2:
                mark = "   <<< CALL"
            print("        0x%05X  %-22s %s %s%s" % (
                x, i.bytes.hex(), i.mnemonic, i.op_str, mark))


if __name__ == "__main__":
    main()
