#!/usr/bin/env python3
"""138: scan a VA range; for each call to 0xb77b10 capture preceding push imm (tag);
for each call 0xb777c0 capture preceding pushes (width, src). Pair tag->width.
"""
import sys
from collections import Counter, defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def dis(lo, hi):
    return list(md.disasm(d[lo - VA:hi - VA], lo))


def main(lo, hi):
    ins = dis(lo, hi)
    tag_votes = Counter()
    pairs = []
    last_tag = None
    pend = []  # recent pushes
    for i, x in enumerate(ins):
        if x.mnemonic == "push":
            pend.append(x.op_str)
        if x.mnemonic == "call":
            t = x.op_str
            if t == "0xb77b10":
                # last push imm
                if pend:
                    p = pend[-1]
                    if p.startswith("0x") or p.isdigit():
                        last_tag = int(p, 0)
                    else:
                        last_tag = None
                pend = []
            elif t == "0xb777c0":
                # pushes: width then ptr. width is the push before last (first pushed)
                if len(pend) >= 1:
                    w = pend[0]
                    pairs.append((last_tag, w))
                    if last_tag is not None and w.startswith("0x"):
                        tag_votes[(last_tag, int(w, 0))] += 1
                pend = []
            else:
                pend = []
    print("== pairs (tag, widthpush) ==")
    for tg, w in pairs:
        print("  tag=%-6s width=%s" % (("0x%02X" % tg) if tg is not None else "?", w))
    print("== tag->width histogram ==")
    for (tg, w), c in sorted(tag_votes.items()):
        print("  tag 0x%02X -> width %d : %d" % (tg, w, c))


if __name__ == "__main__":
    lo = int(sys.argv[1], 0)
    hi = int(sys.argv[2], 0)
    main(lo, hi)
