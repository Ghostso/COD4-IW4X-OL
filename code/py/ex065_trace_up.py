# EX-065 PHASE 1: trace the two callers of sub_8D2A2 upward to the process
# entry / thread start.
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img
from ex065_revalidate_tcls import find_entries, grow

TCLS = r"WeGame\tcls\tcls_core.exe"


def owner_of(img, md, entries, target):
    owners = []
    for c in entries:
        if target in grow(img, c, md):
            owners.append(c)
    return sorted(owners)


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    entries = sorted(find_entries(img))
    print("candidate function entries: %d" % len(entries))

    print()
    print("=" * 78)
    print("owners of the two call sites")
    print("=" * 78)
    for site in (0x8DA49, 0x8DE3C):
        o = owner_of(img, md, entries, site)
        print("   0x%05X owners: %s  -> outermost sub_%X" % (
            site, ["0x%X" % x for x in o[:6]], min(o) if o else 0))

    print()
    print("=" * 78)
    print("context around 0x8DA49")
    print("=" * 78)
    r = 0x8DA00
    n = 0
    while r <= 0x8DA80 and n < 60:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            r += 1
            continue
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
                        s = img.read(t, 90).split(b"\x00")[0]
                        if len(s) >= 4 and all(32 <= c < 127 for c in s):
                            mark += '   ; "%s"' % s.decode()
        star = "   <<<" if r == 0x8DA49 else ""
        print("   0x%05X  %-22s %s %s%s%s" % (
            r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark, star))
        r += insn.size
        n += 1

    print()
    print("=" * 78)
    print("context around 0x8DE3C")
    print("=" * 78)
    r = 0x8DDF0
    n = 0
    while r <= 0x8DE70 and n < 60:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            r += 1
            continue
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
        star = "   <<<" if r == 0x8DE3C else ""
        print("   0x%05X  %-22s %s %s%s%s" % (
            r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark, star))
        r += insn.size
        n += 1


if __name__ == "__main__":
    main()
