# EX-065 PHASE 1: follow the CRT startup to the real application entry
# (main / WinMain / wWinMain) and find the call graph toward sub_8D2A2.
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
    print("0x4B2847  (target of the entry stub jump)")
    print("=" * 78)
    r = 0xB2847
    n = 0
    while n < 120:
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
        # immediate -> string
        if insn.operands:
            for op in insn.operands:
                if op.type == X86_OP_IMM:
                    t = op.imm - img.base
                    if 0 <= t < img.size:
                        s = img.read(t, 100).split(b"\x00")[0]
                        if len(s) >= 5 and all(32 <= c < 127 for c in s):
                            mark += '   ; "%s"' % s.decode()
        print("   0x%05X  %-24s %s %s%s" % (
            r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
        if insn.mnemonic.startswith("ret"):
            break
        r += insn.size
        n += 1
        if n > 115:
            print("   ... (truncated)")

    print()
    print("=" * 78)
    print("find the WinMain registration (the CRT passes the entry to")
    print("__scrt_common_main_seh via an immediate)")
    print("=" * 78)
    # search .text for push imm of a plausible WinMain (a function whose
    # signature takes 4 args and ends with ret 0x10)
    lo, hi = img.codesec()
    cands = []
    for rva in range(0xB2800, 0xB2A20, 1):
        b = img.read(rva, 5)
        if len(b) == 5 and b[0] == 0x68:
            v = int.from_bytes(b[1:5], "little")
            t = v - img.base
            if img.is_code(t):
                cands.append((rva, t))
    for rva, t in cands:
        print("   0x%05X  push 0x%X  (sub_%X)" % (rva, img.base + t, t))


if __name__ == "__main__":
    main()
