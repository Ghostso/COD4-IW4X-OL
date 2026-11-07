# EX-065 PHASE 1: find the CRT's call to the application entry by scanning
# for the main-function table used by __scrt_common_main_seh.
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
    print("MSVC modern CRT: the entry stub calls __scrt_common_main_seh,")
    print("which calls `main` through an immediate reference.")
    print("scan the whole .text for `call` whose target ends with `ret 0x10`")
    print("(WinMain signature) or `ret 0x04`/`ret 0x0C`")
    print("=" * 78)

    # collect all immediate call targets
    lo, hi = img.codesec()
    targets = {}
    r = lo
    while r < hi:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            r += 1
            continue
        if insn.mnemonic == "call" and insn.operands \
                and insn.operands[0].type == X86_OP_IMM:
            t = insn.operands[0].imm - img.base
            if img.is_code(t):
                targets.setdefault(t, []).append(r)
        r += insn.size

    print("distinct immediate call targets: %d" % len(targets))

    # for each, check the ending ret
    print()
    print("targets whose function ends with ret 0x10 (WinMain-like):")
    found = []
    for t in sorted(targets):
        # linear scan up to 4000 bytes for a ret
        rr = t
        n = 0
        while n < 4000:
            insn = next(md.disasm(img.read(rr, 16), img.base + rr), None)
            if insn is None:
                break
            if insn.mnemonic == "ret" and insn.op_str in ("0x10", "0x10 "):
                found.append((t, rr, len(targets[t])))
                break
            if insn.mnemonic.startswith("ret"):
                break
            if insn.mnemonic in ("int3",):
                break
            rr += insn.size
            n += 1
    for t, rr, ncall in found[:60]:
        print("   sub_%-8X  ret at 0x%05X  callers=%d  first=0x%X"
              % (t, rr, ncall, targets[t][0]))
    print("   total: %d" % len(found))

    print()
    print("=" * 78)
    print("the CRT startup file region 0xB2000..0xB3200: all immediate calls")
    print("=" * 78)
    for t, cs_ in sorted(targets.items()):
        for c in cs_:
            if 0xB2000 <= c < 0xB3200:
                print("   0x%05X -> sub_%X" % (c, t))


if __name__ == "__main__":
    main()
