# EX-064 TASK F/G: check whether IIPSLaunchRestore.dll dispatches manager
# slot 5 (offset +0x14) after obtaining the manager pointer.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex064_restore_gpa import Img

RESTORE = r"工具\EX035_DIR\IIPS\IIPSLaunchRestore.dll"


def main():
    img = Img(RESTORE)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("sub_79B0: does it dispatch the manager?")
    print("=" * 78)
    lo, hi = img.codesec()

    def dump(entry, limit=120):
        rva = entry
        n = 0
        while rva < hi and n < limit:
            insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
            if insn is None:
                break
            mark = ""
            if insn.mnemonic == "call" and insn.operands:
                op = insn.operands[0]
                if op.type == X86_OP_MEM and op.mem.base == 0:
                    nm = img.imports.get(op.mem.disp - img.base)
                    if nm:
                        mark = "   ; %s!%s" % nm
                elif op.type == X86_OP_IMM:
                    mark = "   ; -> sub_%X" % (op.imm - img.base)
                elif op.type == X86_OP_REG:
                    mark = "   ; IND %s" % md.reg_name(op.reg)
            print("   0x%05X  %-24s %s %s%s" % (
                rva, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
            if insn.mnemonic.startswith("ret"):
                break
            rva += insn.size
            n += 1

    dump(0x79B0)

    print()
    print("=" * 78)
    print("all [reg+0x14] and [reg+0x68] fetches in IIPSLaunchRestore.dll")
    print("=" * 78)
    for target in (0x14, 0x68, 0x04):
        hits = []
        rva = lo
        while rva < hi:
            insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
            if insn is None:
                rva += 1
                continue
            for o in insn.operands:
                if o.type == X86_OP_MEM and o.mem.disp == target \
                        and o.mem.base != 0 and o.mem.index == 0:
                    hits.append((rva, "%s %s" % (insn.mnemonic, insn.op_str)))
            rva += insn.size
        uniq = {}
        for r, t in hits:
            uniq[r] = t
        print("  [reg+0x%02X] : %d sites" % (target, len(uniq)))
        for r in sorted(uniq)[:20]:
            print("      0x%05X  %s" % (r, uniq[r]))


if __name__ == "__main__":
    main()
