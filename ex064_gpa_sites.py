# EX-064 TASK C/D/H/K: disassemble the two GetResourceManagerII push sites
# in IIPSLaunchRestore.dll and recover the LoadLibrary/GetProcAddress path.
import json

import capstone as cs
import pefile
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

RESTORE = r"工具\EX035_DIR\IIPS\IIPSLaunchRestore.dll"

from ex064_restore_gpa import Img


def main():
    img = Img(RESTORE)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    for name, va, site in (("GetResourceManagerII", 0x1006F43C, 0x3C89),
                           ("GetResourceManagerII", 0x1006F43C, 0x744F),
                           ("ReleaseResourceManagerII", 0x1006F454, 0x3608),
                           ("ReleaseResourceManagerII", 0x1006F454, 0x5CD4)):
        print("=" * 78)
        print("push site 0x%X  ->  \"%s\" (VA 0x%X)" % (site, name, va))
        print("=" * 78)
        lo = site - 0x60
        hi = site + 0x60
        rva = lo
        while rva <= hi:
            insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
            if insn is None:
                rva += 1
                continue
            mark = ""
            if insn.mnemonic == "call" and insn.operands:
                op = insn.operands[0]
                if op.type == X86_OP_MEM and op.mem.base == 0:
                    n = img.imports.get(op.mem.disp - img.base)
                    if n:
                        mark = "   ; %s!%s" % n
                    else:
                        mark = "   ; IAT 0x%X" % op.mem.disp
                elif op.type == X86_OP_IMM:
                    mark = "   ; -> sub_%X" % (op.imm - img.base)
            if insn.mnemonic in ("push", "mov", "lea") and insn.operands:
                op = insn.operands[0]
                if op.type == X86_OP_IMM:
                    t = op.imm - img.base
                    if 0x6C000 <= t < 0x80000:
                        s = img.read(t, 64).split(b"\x00")[0]
                        if s and all(32 <= c < 127 for c in s):
                            mark += '   ; "%s"' % s.decode()
            star = "   <<<" if rva == site else ""
            print("   0x%05X  %-24s %s %s%s%s" % (
                rva, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark, star))
            rva += insn.size
        print()


if __name__ == "__main__":
    main()
