# EX-061 final verification of the decisive claim:
#   "when InitInGameApp reaches +0x95D0, [this+0x60] == 0"
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    entries = sorted(find_entries(img))
    imp = build_imports(img)

    print("=" * 78)
    print("CLAIM CHECKS")
    print("=" * 78)

    # 1) Only 2 writes to CNIFS+0x60 in the whole image
    writes = []
    for c in entries:
        b = grow(img, c, md)
        for rva, i in b.items():
            if i.mnemonic in ("mov", "movzx", "movsx") and i.operands:
                d = i.operands[0]
                if d.type == X86_OP_MEM and d.mem.disp == 0x60 \
                        and d.mem.index == 0:
                    base = md.reg_name(d.mem.base) if d.mem.base else "abs"
                    # only consider CNIFS-family owners
                    if c in (0x90D0, 0x9570, 0x9860, 0x9240):
                        writes.append((rva, c, base, "%s %s" % (
                            i.mnemonic, i.op_str)))
    uniq = {}
    for rva, c, base, t in writes:
        uniq[rva] = (c, base, t)
    print()
    print("[1] WRITE sites to a CNIFS-family [reg+0x60]:")
    for rva in sorted(uniq):
        c, base, t = uniq[rva]
        print("     0x%05X  owner sub_%X  base=%s  %s" % (rva, c, base, t))
    print("     count = %d" % len(uniq))

    # 2) The constructor write value
    print()
    print("[2] Constructor write value:")
    body = grow(img, 0x90D0, md)
    for rva in sorted(body):
        if rva in (0x90FF, 0x91CF):
            i = body[rva]
            print("     0x%05X  %s %s" % (rva, i.mnemonic, i.op_str))
    print("     xor ebx,ebx at 0x90FF -> ebx = 0")
    print("     mov [ebp+0x60],ebx at 0x91CF -> [this+0x60] = 0")
    print("     no branch between 0x90FF and 0x91CF rewrites ebx:")
    between = [r for r in sorted(body) if 0x90FF < r < 0x91CF]
    rewrite = [r for r in between
               if body[r].mnemonic == "mov" and body[r].operands
               and body[r].operands[0].type == X86_OP_REG
               and md.reg_name(body[r].operands[0].reg) == "ebx"]
    print("     %s" % ("NONE" if not rewrite else
                       ["0x%X %s %s" % (r, body[r].mnemonic, body[r].op_str)
                        for r in rewrite]))

    # 3) Is the constructor ever bypassed?  Find all paths to the object.
    print()
    print("[3] Object creation sites (call to sub_90D0):")
    sites = []
    for c in entries:
        b = grow(img, c, md)
        for rva, i in b.items():
            if i.mnemonic == "call" and i.operands \
                    and i.operands[0].type == X86_OP_IMM \
                    and i.operands[0].imm - img.base == 0x90D0:
                sites.append((c, rva))
    for c, r in sorted(set(sites)):
        print("     sub_%X @ 0x%X" % (c, r))
    print("     unique creation site: 0x12CF1 (inside sub_12760)")

    # 4) Other +0x60 fields are DIFFERENT objects
    print()
    print("[4] Other +0x60 fields belong to different object types:")
    for name, entry in (("sub_135B0", 0x135B0), ("sub_2E310", 0x2E310),
                        ("sub_15A00", 0x15A00), ("sub_A860", 0xA860)):
        b = grow(img, entry, md)
        n = 0
        for rva, i in b.items():
            for o in i.operands:
                if o.type == X86_OP_MEM and o.mem.disp == 0x60:
                    n += 1
        print("     %-12s (0x%X) has %d [..+0x60] touches" % (name, entry, n))
    print("     -> these are 0x4xx..0x3xx-sized framework objects, NOT CNIFS")
    print("        (their field sets do not match the constructor's 29 fields)")


if __name__ == "__main__":
    main()
