# EX-065 PHASE 1: recover the dispatch table at .rdata 0x16A4E4 that holds
# sub_8DBEB, and find who iterates it.
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
    print(".rdata region 0x16A480..0x16A560 (around the dispatch entry)")
    print("=" * 78)
    raw = img.rva2raw(0x16A480)
    blob = img.data[raw:raw + 0xE0]
    for off in range(0, 0xE0, 4):
        v = int.from_bytes(blob[off:off + 4], "little")
        rva = 0x16A480 + off
        note = ""
        t = v - img.base
        if img.base <= v < img.base + img.size and img.is_code(t):
            note = "  -> sub_%X" % t
        elif 0x156000 <= v - img.base < 0x1A6000:
            note = "  -> .rdata string"
            o = img.rva2raw(v - img.base)
            if o:
                s = img.data[o:o + 60].split(b"\x00")[0]
                if s and all(32 <= c < 127 for c in s):
                    note += ' "%s"' % s.decode()
        print("   0x%05X  %08X%s" % (rva, v, note))

    print()
    print("=" * 78)
    print("who references RVA 0x16A4E4 / the table base?")
    print("=" * 78)
    for target in (0x16A4E4, 0x16A4E0, 0x16A4C8, 0x16A480):
        needle = (img.base + target).to_bytes(4, "little")
        st = 0
        out = []
        while True:
            i = img.data.find(needle, st)
            if i < 0:
                break
            rva, sec = img.raw2rva(i)
            out.append((i, rva, sec))
            st = i + 1
        print("   VA 0x%X : %d refs %s" % (
            img.base + target, len(out),
            [("0x%X" % r) for _, r, _ in out[:8]]))

    print()
    print("=" * 78)
    print("sub_8DBEB body")
    print("=" * 78)
    r = 0x8DBEB
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
        print("   0x%05X  %-22s %s %s%s" % (
            r, insn.bytes.hex(), insn.mnemonic, insn.op_str, mark))
        if insn.mnemonic.startswith("ret"):
            break
        r += insn.size
        n += 1


if __name__ == "__main__":
    main()
