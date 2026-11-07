# EX-061: validate each +0x60 site as real code (reachable by a valid
# decode from a function entry) vs a misaligned data false positive.
import json
from collections import OrderedDict

import capstone as cs

from ex060_iips_cfg import Image, DLL
from ex061_functions import find_prologues, grow, code_bounds


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    lo, hi = code_bounds(img)

    # Build the union of all decoded instruction addresses across all
    # strict-prologue function bodies.
    starts = sorted(find_prologues(img))
    decoded = set()
    for c in starts:
        b = grow(img, c, md)
        decoded.update(b.keys())
    print("union of strict-function instruction addresses: %d" % len(decoded))

    sites = [0x91CF, 0x929F, 0x92C6, 0x92C9,
             0x95D0, 0x97A9,
             0x9A2B, 0x9B51, 0x9B66, 0x9B7B,
             0xA327, 0xA340, 0xA4D9, 0xA613, 0xA639, 0xA68E, 0xA93A,
             0xB0D0, 0xB0D6, 0xCBA0, 0xCBA6,
             0x13629, 0x1366E, 0x13698, 0x1384A, 0x1385E, 0x138D3,
             0x15747, 0x15CF4, 0x2F01C]

    print()
    print("=== site validation ===")
    real, fake = [], []
    for s in sorted(sites):
        ok = s in decoded
        (real if ok else fake).append(s)
        # show context bytes either way
        ctx = img.by_rva[s - 4:s + 6]
        print("  +0x%05X  valid_code=%-5s  bytes=%s" % (s, ok, ctx.hex()))

    print()
    print("VALID:", " ".join("+0x%X" % x for x in real))
    print("INVALID/UNATTRIBUTED:", " ".join("+0x%X" % x for x in fake))


if __name__ == "__main__":
    main()
