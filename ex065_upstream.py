# EX-065 PHASE 1: trace the constructor callers (0x5EB8B etc.) upward to
# the process startup / WinMain.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex065_tcls_img import Img
from ex065_revalidate_tcls import find_entries, grow

TCLS = r"WeGame\tcls\tcls_core.exe"


def owner_of(img, md, entries, target):
    owners = [c for c in entries if target in grow(img, c, md)]
    return sorted(owners)


def callers_of(img, md, target):
    lo, hi = img.codesec()
    hits = []
    r = lo
    while r < hi:
        insn = next(md.disasm(img.read(r, 16), img.base + r), None)
        if insn is None:
            r += 1
            continue
        if insn.mnemonic == "call" and insn.operands \
                and insn.operands[0].type == X86_OP_IMM \
                and insn.operands[0].imm - img.base == target:
            hits.append(r)
        r += insn.size
    return hits


def main():
    img = Img(TCLS)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    entries = sorted(find_entries(img))

    level = [0x5EB8B, 0x5EE3D, 0x5F30A, 0x5F5E5]
    seen = set()
    depth = 0
    while level and depth < 4:
        nxt = []
        print("=" * 78)
        print("LEVEL %d : %s" % (depth, ["0x%X" % x for x in level]))
        print("=" * 78)
        for s in level:
            o = owner_of(img, md, entries, s)
            if not o:
                print("   site 0x%05X : owner UNKNOWN" % s)
                continue
            f = min(o)
            print("   site 0x%05X owner sub_%X" % (s, f))
            if f in seen:
                continue
            seen.add(f)
            c2 = callers_of(img, md, f)
            print("        callers of sub_%X : %s" % (
                f, ["0x%X" % x for x in c2[:10]]))
            nxt.extend(c2)
        level = nxt
        depth += 1


if __name__ == "__main__":
    main()
