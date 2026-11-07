# EX-065 PHASE 1: the two sub_8D2A2 callers are state handlers. Find the
# dispatcher / caller chain up to the process entry.
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img
from ex065_revalidate_tcls import find_entries, grow

TCLS = r"WeGame\tcls\tcls_core.exe"


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    lo, hi = img.codesec()

    print("=" * 78)
    print("callers of sub_8D9ED and sub_8DBEB")
    print("=" * 78)
    for target in (0x8D9ED, 0x8DBEB):
        hits = []
        r = lo
        while r < hi:
            insn = next(md.disasm(img.read(r, 16), img.base + r), None)
            if insn is None:
                r += 1
                continue
            if insn.mnemonic == "call" and insn.operands \
                    and insn.operands[0].type == X86_OP_IMM \
                    and insn.operands[0].imm - img.base == target:
                hits.append(r)
            r += insn.size
        print("   sub_%X : %d callers %s" % (
            target, len(hits), ["0x%X" % x for x in hits[:10]]))

    print()
    print("=" * 78)
    print("function-pointer occurrences of sub_8D9ED / sub_8DBEB")
    print("=" * 78)
    for target in (0x8D9ED, 0x8DBEB):
        needle = (img.base + target).to_bytes(4, "little")
        st = 0
        out = []
        while True:
            i = img.data.find(needle, st)
            if i < 0:
                break
            rva, sec = img.raw2rva(i)
            out.append((i, rva, sec))
            st = i + 1
        print("   sub_%X : %d occurrences" % (target, len(out)))
        for i, rva, sec in out:
            print("      raw 0x%06X RVA 0x%06X sec %s" % (i, rva, sec))

    print()
    print("=" * 78)
    print("sub_8D9ED prologue (what is [ebp-4], the state object?)")
    print("=" * 78)
    r = 0x8D9ED
    n = 0
    while n < 50:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            break
        mark = ""
        if insn.mnemonic == "call" and insn.operands:
            op = insn.operands[0]
            if op.type == X86_OP_IMM:
                mark = "   ; -> sub_%X" % (op.imm - img.base)
            elif op.type == X86_OP_MEM and op.mem.base == 0:
                nm = img.imports.get(op.mem.disp - img.base)
                if nm:
                    mark = "   ; %s!%s" % nm
        print("   0x%05X  %-22s %s %s%s" % (
            r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
        if insn.mnemonic.startswith("ret"):
            break
        r += insn.size
        n += 1


if __name__ == "__main__":
    main()
