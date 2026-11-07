# EX-065 PHASE 1: find the code that iterates the handler table containing
# sub_8DBEB (RVA 0x16A4DC region) and the command strings.
import json
import re

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img

TCLS = r"WeGame\tcls\tcls_core.exe"


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("strings in .rdata near 0x16A4DC (the handler table)")
    print("=" * 78)
    for m in re.finditer(rb"[ -~]{5,}", img.data):
        rva, sec = img.raw2rva(m.start())
        if rva is None or sec != ".rdata":
            continue
        if 0x16A300 <= rva <= 0x16A700:
            print("   RVA 0x%06X VA 0x%08X  %r" % (
                rva, img.base + rva, m.group()))

    print()
    print("=" * 78)
    print("the table 0x16A4D8..0x16A544 interpreted as dwords")
    print("=" * 78)
    for rva in range(0x16A4D8, 0x16A548, 4):
        v = int.from_bytes(img.read(rva, 4), "little")
        t = v - img.base
        note = ""
        if img.base <= v < img.base + img.size and img.is_code(t):
            note = "code sub_%X" % t
        else:
            o = img.rva2raw(t)
            if o is not None:
                s = img.data[o:o + 40].split(b"\x00")[0]
                if s and all(32 <= c < 127 for c in s):
                    note = 'str "%s"' % s.decode()
        print("   0x%05X  %08X  %s" % (rva, v, note))

    print()
    print("=" * 78)
    print("who loads the table base? immediates in 0x56A4C0..0x56A550")
    print("=" * 78)
    lo, hi = img.codesec()
    r = lo
    while r < hi:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            r += 1
            continue
        for op in insn.operands:
            if op.type == X86_OP_IMM and 0x56A4C0 <= op.imm <= 0x56A550:
                print("   0x%05X  %-22s %s %s" % (
                    r, insn.bytes.hex(), insn.mnemonic, insn.op_str))
        r += insn.size


if __name__ == "__main__":
    main()
