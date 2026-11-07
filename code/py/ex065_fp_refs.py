# EX-065 PHASE 1: are sub_5EA85 / sub_5F4A1 reached by function pointer,
# vtable, or export?  Also recover their structure.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img

TCLS = r"WeGame\tcls\tcls_core.exe"


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("function-pointer / vtable references")
    print("=" * 78)
    for name, t in (("sub_5EA85", 0x5EA85), ("sub_5F4A1", 0x5F4A1)):
        needle = (img.base + t).to_bytes(4, "little")
        st = 0
        out = []
        while True:
            i = img.data.find(needle, st)
            if i < 0:
                break
            rva, sec = img.raw2rva(i)
            out.append((i, rva, sec))
            st = i + 1
        print("   %s (0x%X) : %d occurrences" % (name, t, len(out)))
        for i, rva, sec in out:
            print("      raw 0x%06X RVA 0x%06X sec %s" % (i, rva, sec))

    # exports
    print()
    print("   exports of tcls_core.exe:")
    if hasattr(img.pe, "DIRECTORY_ENTRY_EXPORT"):
        for e in img.pe.DIRECTORY_ENTRY_EXPORT.symbols:
            print("      %s RVA 0x%X" % (
                e.name.decode() if e.name else "ord%d" % e.ordinal, e.address))
    else:
        print("      (none)")

    print()
    print("=" * 78)
    print("sub_5EA85 prologue / body head")
    print("=" * 78)
    r = 0x5EA85
    n = 0
    while n < 70:
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
        if insn.mnemonic.startswith("ret"):
            break
        r += insn.size
        n += 1


if __name__ == "__main__":
    main()
