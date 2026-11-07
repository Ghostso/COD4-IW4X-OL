# EX-061 TASK 5/6: locate the CNIFS factory entry and its callers, so the
# full lifecycle chain (ctor -> initIfsLib -> dtor) can be established.
import json
from collections import OrderedDict, defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imp = build_imports(img)
    entries = sorted(find_entries(img))

    # The function that owns 0x12CF1: find the OUTERMOST entry whose body
    # contains 0x12CF1.
    cache = {}

    def body(c):
        if c not in cache:
            cache[c] = grow(img, c, md)
        return cache[c]

    owners = [c for c in entries if 0x12CF1 in body(c)]
    print("functions containing 0x12CF1 (ctor call site):")
    for o in sorted(owners):
        print("   sub_%X  (%d insns)" % (o, len(body(o))))
    factory = min(owners)
    print("=> outermost factory entry: sub_%X" % factory)

    print()
    print("=" * 78)
    print("factory prologue + allocation sequence")
    print("=" * 78)
    fb = body(factory)
    for rva in sorted(fb):
        if factory <= rva <= factory + 0x40:
            i = fb[rva]
            mark = ""
            if i.mnemonic == "call" and i.operands:
                op = i.operands[0]
                if op.type == X86_OP_IMM:
                    mark = "  ; -> sub_%X" % (op.imm - img.base)
            print("   0x%05X  %-20s %s %s%s" % (
                rva, i.bytes.hex(), i.mnemonic, i.op_str, mark))

    print()
    print("=" * 78)
    print("callers of the factory sub_%X" % factory)
    print("=" * 78)
    hits = []
    for c in entries:
        b = body(c)
        for rva, insn in b.items():
            if insn.mnemonic == "call" and insn.operands:
                op = insn.operands[0]
                if op.type == X86_OP_IMM and op.imm - img.base == factory:
                    hits.append((c, rva))
    print("   immediate callers: %d" % len(set(c for c, r in hits)))
    for c, r in sorted(set(hits)):
        print("      from sub_%X at 0x%X" % (c, r))

    print()
    print("=" * 78)
    print("export table again (factory may be reached only via vtable)")
    print("=" * 78)
    for e in img.pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if e.name:
            print("   %-26s RVA 0x%X" % (e.name.decode(), e.address))


if __name__ == "__main__":
    main()
