# EX-061: resolve the UNKNOWN owner sites by finding a valid instruction
# boundary and growing backwards to the nearest real function entry.
import json
from collections import OrderedDict, deque

import capstone as cs

from ex060_iips_cfg import Image, DLL
from ex061_functions import find_prologues, grow, code_bounds


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    starts = set(find_prologues(img))

    sites = [0xB0D0, 0xB0D6, 0xCBA0, 0xCBA6, 0x13629, 0x1366E, 0x13698,
             0x1384A, 0x1385E, 0x138D3, 0x15747, 0x2F01C]

    # Are these addresses even valid instruction boundaries reached by a
    # linear decode from .text start, or are they inside data?
    lo, hi = code_bounds(img)
    print("=== boundary validity check ===")
    for s in sites:
        # walk from the nearest 0x1000-aligned start and see if we land on s
        landed = False
        anchor = (s // 0x1000) * 0x1000
        rva = max(anchor, lo)
        while rva < s:
            insn = next(md.disasm(img.read(rva, 16), img.base + rva), None)
            if insn is None:
                break
            rva += insn.size
        landed = (rva == s)
        print("  +0x%05X  align_from_0x%X landed=%s (stopped at 0x%X)"
              % (s, anchor, landed, rva))

    print()
    print("=== wider prologue search: treat any byte after ret/int3 as entry ===")
    d = img.by_rva
    extra = set()
    for rva in range(lo, hi - 4):
        prev = d[rva - 1] if rva > lo else 0
        if prev in (0xC3, 0xCC) and d[rva] in (0x55, 0x6A, 0x64, 0x83, 0x81):
            extra.add(rva)
    allstarts = starts | extra
    print("  starts after widening: %d (+%d)" % (len(allstarts),
                                                 len(allstarts) - len(starts)))

    print()
    print("=== owner via widened entries ===")
    cache = {}

    def body(c):
        if c not in cache:
            cache[c] = grow(img, c, md)
        return cache[c]

    for s in sites:
        cands = [x for x in allstarts if x <= s]
        owners = [c for c in cands if s in body(c)]
        if not owners:
            print("  +0x%05X  owner STILL UNKNOWN" % s)
            continue
        owner = min(owners)
        b = body(owner)
        print("  +0x%05X  owner +0x%05X  body ..0x%05X  insns=%d" % (
            s, owner, max(b.keys()), len(b)))


if __name__ == "__main__":
    main()
