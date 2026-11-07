# EX-065 PHASE 1 (decisive): find every caller of sub_8D2A2 and the path
# from the process entry.
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

    print("=" * 78)
    print("every reference to sub_8D2A2 in tcls_core.exe")
    print("=" * 78)
    # direct calls
    lo, hi = img.codesec()
    direct = []
    regs = []
    r = lo
    while r < hi:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            r += 1
            continue
        if insn.mnemonic == "call" and insn.operands:
            op = insn.operands[0]
            if op.type == X86_OP_IMM and op.imm - img.base == 0x8D2A2:
                direct.append(r)
            elif op.type == X86_OP_MEM and op.mem.base == 0:
                nm = img.imports.get(op.mem.disp - img.base)
                if nm and "CreateThr" in nm[1]:
                    regs.append((r, nm))
        r += insn.size
    print("   direct CALL 0x48D2A2 : %d  %s" % (
        len(direct), ["0x%X" % x for x in direct]))

    # function pointer occurrences
    needle = (img.base + 0x8D2A2).to_bytes(4, "little")
    st = 0
    fp = []
    while True:
        i = img.data.find(needle, st)
        if i < 0:
            break
        rva, sec = img.raw2rva(i)
        fp.append((i, rva, sec))
        st = i + 1
    print("   le32 function-pointer occurrences: %d" % len(fp))
    for i, rva, sec in fp:
        print("      raw 0x%06X RVA 0x%06X sec %s" % (i, rva, sec))

    print()
    print("   CreateThread / _beginthreadex references:")
    for r, nm in regs[:20]:
        print("      0x%05X %s!%s" % (r, nm[0], nm[1]))


if __name__ == "__main__":
    main()
