# -*- coding: utf-8 -*-
import os, re
p = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\accepted_state.txt"
sam = [l for l in open(p, encoding="utf-8", errors="replace").read().splitlines() if " SAM " in l]
armed = [l for l in sam if ("this278=0x0101" in l or "this278=0x0001" in l)]
print("SAM total =", len(sam), " SAM armed =", len(armed))
for l in armed:
    print("   ", l[:150])
print()
g2s = {}
for l in sam:
    m = re.search(r"G2=([0-9A-Fa-fx]+)", l)
    if m: g2s[m.group(1)] = g2s.get(m.group(1), 0) + 1
print("SAM G2 distribution:", g2s)
g3s = {}
for l in sam:
    m = re.search(r"G3=(-?\d+)", l)
    if m: g3s[m.group(1)] = g3s.get(m.group(1), 0) + 1
print("SAM G3 distribution:", g3s)
# also non-SAM armed rows: their G2/G3 not printed; report separately
