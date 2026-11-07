# EX-065 PHASE 1: locate the real application entry (the CRT's
# __initterm / function table at 0x5B7AE4) and follow it to sub_8D2A2.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img

TCLS = r"WeGame\tcls\tcls_core.exe"


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    # The CRT calls the main function through a pointer loaded from
    # [0x5B7AE4].  Find the immediate that initialises that global.
    print("=" * 78)
    print("global 0x5B7AE4 (CRT main-function pointer slot)")
    print("=" * 78)
    needle = (0x5B7AE4).to_bytes(4, "little")
    st = 0
    hits = []
    while True:
        i = img.data.find(needle, st)
        if i < 0:
            break
        rva, sec = img.raw2rva(i)
        hits.append((i, rva, sec))
        st = i + 1
    for i, rva, sec in hits:
        print("  raw 0x%06X  RVA 0x%06X  sec %s" % (i, rva, sec))
    print("  total: %d" % len(hits))

    print()
    print("=" * 78)
    print("writes/reads of 0x5B7AE4 in .text")
    print("=" * 78)
    lo, hi = img.codesec()
    r = lo
    while r < hi:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            r += 1
            continue
        for op in insn.operands:
            if op.type == X86_OP_MEM and op.mem.base == 0 \
                    and op.mem.disp == 0x5B7AE4:
                print("   0x%05X  %-24s %s %s" % (
                    r, insn.bytes.hex(), insn.mnemonic, insn.op_str))
        r += insn.size

    print()
    print("=" * 78)
    print("candidate: which function pointer is stored into the CRT slot?")
    print("=" * 78)
    print("""
  The CRT sequence at 0xB2853..0xB295D calls the application entry
  indirectly.  Look for the immediate assignment used by the CRT's
  `__scrt_common_main_seh` before the indirect call.
""")
    # scan for mov [0x5B7AE4-like], imm  OR  push imm + call near 0xB28E0
    for r in range(0xB2800, 0xB2A20):
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            continue
        if insn.mnemonic == "push" and insn.operands \
                and insn.operands[0].type == X86_OP_IMM:
            t = insn.operands[0].imm - img.base
            if img.is_code(t) and 0x1000 <= t < hi:
                s = img.read(t, 8)
                # heuristics: candidate WinMain prologue
                if s[:3] in (b"\x55\x8b\xec", b"\x6a\xff\x68") or \
                        s[0:1] == b"\x53":
                    print("   possible entry push at 0x%05X -> 0x%X (sub_%X)"
                          " bytes %s" % (r, insn.operands[0].imm, t, s.hex()))


if __name__ == "__main__":
    main()
