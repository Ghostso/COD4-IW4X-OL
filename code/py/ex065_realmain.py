# EX-065 PHASE 1: resolve tcls_core.exe's real application entry by
# following the CRT's invoke_main and the static-initializer table.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img

TCLS = r"WeGame\tcls\tcls_core.exe"


def dump(img, md, entry, limit=80, title=None):
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
            if op.type == X86_OP_MEM and op.mem.base == 0:
                nm = img.imports.get(op.mem.disp - img.base)
                mark = "   ; %s!%s" % nm if nm else "   ; IAT 0x%X" % op.mem.disp
            elif op.type == X86_OP_MEM:
                mark = "   ; IND [%s+0x%X]" % (
                    md.reg_name(op.mem.base) if op.mem.base else "-",
                    op.mem.disp)
            elif op.type == X86_OP_REG:
                mark = "   ; IND %s" % md.reg_name(op.reg)
            elif op.type == X86_OP_IMM:
                mark = "   ; -> sub_%X" % (op.imm - img.base)
        if insn.operands:
            for op in insn.operands:
                if op.type == X86_OP_IMM:
                    t = op.imm - img.base
                    if 0 <= t < img.size:
                        s = img.read(t, 90).split(b"\x00")[0]
                        if len(s) >= 5 and all(32 <= c < 127 for c in s):
                            mark += '   ; "%s"' % s.decode()
        print("   0x%05X  %-24s %s %s%s" % (
            r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
        if insn.mnemonic.startswith("ret") or insn.mnemonic == "int3":
            break
        r += insn.size
        n += 1


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    # The CRT's invoke_main path ends in sub_D74F7 -> sub_D909C etc.
    # In MSVC that is __scrt_common_main_seh -> main.
    # Trace the chain: sub_D909C / sub_D96DF / sub_D9217
    for entry in (0xD909C, 0xD96DF, 0xD9217, 0xD80B6, 0xD9268, 0xD9708):
        dump(img, md, entry, 40, "sub_%X" % entry)
        print()


if __name__ == "__main__":
    main()
