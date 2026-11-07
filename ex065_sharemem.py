# EX-065 PHASE 3: disassemble the TCLS shared-memory / mutex / window name
# construction sites in tcls_core.exe.
import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img

TCLS = r"WeGame\tcls\tcls_core.exe"


def wide_at(img, rva, limit=80):
    raw = img.rva2raw(rva)
    if raw is None:
        return ""
    s = img.data[raw:raw + limit]
    try:
        t = s.decode("utf-16-le").split("\x00")[0]
    except Exception:
        return ""
    if 3 < len(t) < 60 and all(32 <= ord(c) < 127 for c in t):
        return t
    return ""


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    for site, title in ((0x798E, "TCLS_SHAREDMEMEMORY%s%lu use #1"),
                        (0x40B9, "use #2"),
                        (0xC629, "TCLS_CORE_SHARE_MEMORY_"),
                        (0xC77F, "TCLS_CORE_MUTEX_"),
                        (0x18F57, "TCLS_CORE_WND_")):
        print("=" * 72)
        print("%s @ 0x%X" % (title, site))
        print("=" * 72)
        r = site - 0x40
        n = 0
        while r <= site + 0x60 and n < 60:
            insn = next(md.disasm(img.read(r, 16), img.base + r), None)
            if insn is None:
                r += 1
                continue
            mark = ""
            if insn.mnemonic == "call" and insn.operands:
                op = insn.operands[0]
                if op.type == X86_OP_MEM and op.mem.base == 0:
                    nm = img.imports.get(op.mem.disp - img.base)
                    if nm:
                        mark = "  ; %s!%s" % nm
                elif op.type == X86_OP_IMM:
                    mark = "  ; -> sub_%X" % (op.imm - img.base)
                elif op.type == X86_OP_REG:
                    mark = "  ; IND %s" % md.reg_name(op.reg)
            if insn.operands:
                for op in insn.operands:
                    if op.type == X86_OP_IMM:
                        t = op.imm - img.base
                        w = wide_at(img, t)
                        if w:
                            mark += '  ; L"%s"' % w
            star = "  <<<" if r == site else ""
            print("  %05X  %-22s %s %s%s%s" % (
                r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark, star))
            r += insn.size
            n += 1
        print()


if __name__ == "__main__":
    main()
