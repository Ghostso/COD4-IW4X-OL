# EX-063 TASK C/F/G: trace the exported factory's global publication of the
# manager object and find who dispatches its slot 1.
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow

GLOBALS = [0x1004EB68, 0x1004EB70, 0x1004EB6C, 0x1004EB74]


def main():
    img = Image(DLL)
    base = img.base
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    entries = sorted(find_entries(img))

    print("=" * 78)
    print("the four export-cache globals")
    print("=" * 78)
    for g in GLOBALS:
        print("   0x%X" % g)

    print()
    print("=" * 78)
    print("all accesses to 0x1004EB68 (the manager singleton)")
    print("=" * 78)
    cache = {}
    for c in entries:
        b = grow(img, c, md)
        cache[c] = b
    for g in GLOBALS:
        hits = []
        for c, b in cache.items():
            for rva, i in b.items():
                for oi, o in enumerate(i.operands):
                    if o.type == X86_OP_MEM and o.mem.base == 0 \
                            and o.mem.disp == g:
                        kind = "WRITE" if (i.mnemonic in ("mov", "or", "and",
                                                          "add", "sub")
                                           and oi == 0) else "READ"
                        hits.append((rva, c, kind,
                                     "%s %s" % (i.mnemonic, i.op_str)))
        uniq = OrderedDict()
        for rva, c, k, t in hits:
            uniq[rva] = (c, k, t)
        print()
        print("  -- global 0x%X : %d sites" % (g, len(uniq)))
        for rva in sorted(uniq):
            c, k, t = uniq[rva]
            print("      0x%05X sub_%-8X %-5s %s" % (rva, c, k, t))

    print()
    print("=" * 78)
    print("who dispatches the manager's slot +0x04 (= sub_197F0)?")
    print("=" * 78)
    print("""
  from sub_1A270 (manager vtable slot 5) at 0x1A2FC:
       mov ecx, [esi+0x19C]     ; a MANAGER object (not the singleton)
       mov eax, [ecx]
       mov edx, [eax+4]         ; slot 1 = sub_197F0
       call edx

  `esi` is sub_1A270's own `this` (mov esi, ecx at 0x1A285), i.e. the
  MANAGER instance.  So the manager holds a MANAGER pointer at +0x19C.
""")

    print("=" * 78)
    print("writers of [X+0x19C] that could store a manager (not CNIFS)")
    print("=" * 78)
    for rva, c, t in []:
        pass
    targets = [0x122AC, 0x12D06, 0x13040, 0x137AB]
    for rva in targets:
        for c, b in cache.items():
            if rva in b:
                i = b[rva]
                print("   0x%05X sub_%-8X %s %s" % (
                    rva, c, i.mnemonic, i.op_str))
                break

    print()
    print("=" * 78)
    print("is sub_11F20 able to store the manager into its own +0x19C?")
    print("=" * 78)
    b = grow(img, 0x11F20, md)
    for rva in sorted(b):
        i = b[rva]
        if "0x19c" in i.op_str:
            print("   0x%05X  %s %s" % (rva, i.mnemonic, i.op_str))


if __name__ == "__main__":
    main()
