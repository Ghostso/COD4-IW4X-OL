# EX-061 TASK 4/6: find who constructs the CNIFS object, and whether the
# constructor provably runs before CNIFS::InitInGameApp.
import json
from collections import OrderedDict, defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_ECX, X86_REG_EBP

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    entries = sorted(find_entries(img))

    print("=" * 78)
    print("call sites targeting sub_90D0 (CNIFS ctor), sub_9240 (dtor),")
    print("sub_9570 (initIfsLib), sub_9860 (InitInGameApp)")
    print("=" * 78)
    targets = {
        "CNIFS::ctor   sub_90D0": 0x90D0,
        "CNIFS::dtor   sub_9240": 0x9240,
        "initIfsLib    sub_9570": 0x9570,
        "InitInGameApp sub_9860": 0x9860,
    }

    found = defaultdict(list)
    for c in entries:
        body = grow(img, c, md)
        for rva, insn in body.items():
            if insn.mnemonic != "call" or not insn.operands:
                continue
            op = insn.operands[0]
            if op.type == X86_OP_IMM:
                t = op.imm - img.base
                if t in targets.values():
                    found[t].append((c, rva))

    for name, t in targets.items():
        print()
        print("  %s : %d immediate callers" % (name, len(found[t])))
        seen = set()
        for owner, rva in sorted(found[t]):
            key = (owner, rva)
            if key in seen:
                continue
            seen.add(key)
            print("      from sub_%X at 0x%X" % (owner, rva))

    print()
    print("=" * 78)
    print("Exports of iips.dll (factory entry points)")
    print("=" * 78)
    for e in img.pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if e.name:
            print("   %-26s RVA 0x%X" % (e.name.decode(), e.address))

    print()
    print("=" * 78)
    print("Who calls the exported factories internally?")
    print("=" * 78)
    for e in img.pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if not e.name:
            continue
        t = e.address
        hits = []
        for c in entries:
            body = grow(img, c, md)
            for rva, insn in body.items():
                if insn.mnemonic == "call" and insn.operands \
                        and insn.operands[0].type == X86_OP_IMM \
                        and insn.operands[0].imm - img.base == t:
                    hits.append((c, rva))
        print("   %-26s (0x%X) immediate callers=%d" % (
            e.name.decode(), t, len(hits)))
        for owner, rva in sorted(hits)[:10]:
            print("        sub_%X @ 0x%X" % (owner, rva))


if __name__ == "__main__":
    main()
