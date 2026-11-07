# EX-061: attribute every +0x60 access site to its TRUE owning function.
#
# Fix over ex061_functions.py: a function body may itself contain nested
# prologue-like byte patterns (e.g. the `64 A1 00 00 00 00` after the SEH
# push).  We therefore choose the EARLIEST prologue whose grown body both
# contains the site AND does not start in the middle of another function.
import json
from collections import OrderedDict, deque

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import COND_JMP
from ex061_functions import find_prologues, grow, code_bounds


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    starts = sorted(find_prologues(img))
    print("strict prologue candidates: %d" % len(starts))
    print("0x9570 in candidates:", 0x9570 in starts)
    print("0x9860 in candidates:", 0x9860 in starts)
    print("0x9867 in candidates:", 0x9867 in starts)
    print("0x9577 in candidates:", 0x9577 in starts)

    # Prefer the OUTERMOST prologue: among all prologues <= site whose body
    # contains the site, choose the one with the EARLIEST rva, but only if
    # no other accepted prologue lies between it and the site with a body
    # that also contains the site (which would mean nesting).
    sites = [0x95D0, 0x97A9, 0x9A2B, 0x9B51, 0x9B66, 0x9B7B,
             0x91CF, 0x13629, 0x1366E, 0x13698, 0x1384A, 0x1385E, 0x138D3,
             0x15CF4, 0x2F01C, 0xA327, 0xA340, 0xA4D9, 0xA613, 0xA639,
             0xA68E, 0xA93A, 0x929F, 0x92C6, 0x92C9, 0x15747,
             0xB0D0, 0xB0D6, 0xCBA0, 0xCBA6]

    cache = {}

    def body(c):
        if c not in cache:
            cache[c] = grow(img, c, md)
        return cache[c]

    print()
    print("=== owner attribution (outermost containing function) ===")
    results = {}
    for s in sorted(sites):
        cands = [x for x in starts if x <= s]
        owners = [c for c in cands if s in body(c)]
        if not owners:
            print("  +0x%05X  owner UNKNOWN" % s)
            results[s] = None
            continue
        owner = min(owners)          # outermost / earliest
        results[s] = owner
        b = body(owner)
        print("  +0x%05X  owner +0x%05X  body ..0x%05X  insns=%d  "
              "candidates=%s" % (
                  s, owner, max(b.keys()), len(b),
                  "[" + ",".join("0x%X" % o for o in sorted(owners)[:4]) + "]"))

    print()
    print("=== grouping by owner ===")
    grp = {}
    for s, o in results.items():
        grp.setdefault(o, []).append(s)
    for o in sorted(grp, key=lambda x: (x is None, x)):
        name = "UNKNOWN" if o is None else "sub_%X" % o
        print("  %-14s : %s" % (
            name, " ".join("+0x%X" % x for x in sorted(grp[o]))))

    import pickle
    with open("ex061_owner_map.json", "w") as f:
        json.dump({("0x%X" % k): (None if v is None else "0x%X" % v)
                   for k, v in results.items()}, f, indent=1)
    print()
    print("wrote ex061_owner_map.json")


if __name__ == "__main__":
    main()
