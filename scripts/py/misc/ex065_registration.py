# EX-065 PHASE 1: recover the code that registers the handler table
# (0x89F4C / 0x8A0AD) and trace it to the process startup.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img
from ex065_revalidate_tcls import find_entries, grow

TCLS = r"WeGame\tcls\tcls_core.exe"


def dump(img, md, entry, limit=70, title=None):
    print("=" * 78)
    print(title or ("disassembly from 0x%X" % entry))
    print("=" * 78)
    r = entry
    n = 0
    while n < limit:
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
            elif op.type == X86_OP_MEM:
                mark = "   ; IND [%s+0x%X]" % (
                    md.reg_name(op.mem.base) if op.mem.base else "-",
                    op.mem.disp)
            elif op.type == X86_OP_REG:
                mark = "   ; IND %s" % md.reg_name(op.reg)
        if insn.operands:
            for op in insn.operands:
                if op.type == X86_OP_IMM:
                    t = op.imm - img.base
                    if 0 <= t < img.size:
                        s = img.read(t, 80).split(b"\x00")[0]
                        if len(s) >= 5 and all(32 <= c < 127 for c in s):
                            mark += '   ; "%s"' % s.decode()
        print("   0x%05X  %-22s %s %s%s" % (
            r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
        if insn.mnemonic.startswith("ret") or insn.mnemonic == "int3":
            break
        r += insn.size
        n += 1


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    entries = sorted(find_entries(img))

    for site in (0x89F4C, 0x8A0AD):
        owners = [c for c in entries if site in grow(img, c, md)]
        print("=" * 78)
        print("site 0x%05X owners: %s -> sub_%X" % (
            site, ["0x%X" % x for x in owners[:6]], min(owners)))
        print("=" * 78)
        dump(img, md, min(owners), 60, "function containing 0x%05X" % site)
        print()

    print()
    print("=" * 78)
    print("callers of those registration functions")
    print("=" * 78)
    for site in (0x89F4C, 0x8A0AD):
        owners = [c for c in entries if site in grow(img, c, md)]
        t = min(owners)
        hits = []
        lo, hi = img.codesec()
        r = lo
        while r < hi:
            insn = next(md.disasm(img.read(r, 16), img.base + r), None)
            if insn is None:
                r += 1
                continue
            if insn.mnemonic == "call" and insn.operands \
                    and insn.operands[0].type == X86_OP_IMM \
                    and insn.operands[0].imm - img.base == t:
                hits.append(r)
            r += insn.size
        print("   sub_%X : %d callers %s" % (t, len(hits),
                                             ["0x%X" % x for x in hits[:10]]))


if __name__ == "__main__":
    main()
