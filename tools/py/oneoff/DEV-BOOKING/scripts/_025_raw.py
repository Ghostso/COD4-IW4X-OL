# -*- coding: utf-8 -*-
import os
p = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\accepted_state.txt"
lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
print("total lines =", len(lines))
idx = [i for i, l in enumerate(lines) if " CHG " in l]
print("first CHG at line index", idx[0] if idx else None)
if idx:
    s = max(0, idx[0] - 6)
    for i in range(s, min(len(lines), s + 16)):
        print("%5d | %s" % (i, lines[i][:150]))
print()
# SAM rows with this278 != 0xFFFF
sam = [l for l in lines if " SAM " in l]
nz = [l for l in sam if "this278=0xFFFF" not in l]
print("SAM total =", len(sam), " SAM with this278 != 0xFFFF =", len(nz))
for l in nz[:10]:
    print("   ", l[:160])
print()
# timestamps of SAM with 0xFFFF vs not
import re
def ts(l):
    m = re.match(r"\[(\d\d:\d\d:\d\d\.\d+)\]", l)
    return m.group(1) if m else None
if nz:
    print("first SAM non-FFFF ts =", ts(nz[0]), " last =", ts(nz[-1]))
    print("first SAM FFFF ts =", ts(sam[0]), " last FFFF ts =", ts([l for l in sam if 'this278=0xFFFF' in l][-1]))
