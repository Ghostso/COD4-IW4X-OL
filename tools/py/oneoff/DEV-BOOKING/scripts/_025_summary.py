# -*- coding: utf-8 -*-
import re
from collections import Counter
p = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\accepted_state.txt"
sam = [l for l in open(p, encoding="utf-8", errors="replace").read().splitlines() if " SAM " in l]
def f(l, k):
    m = re.search(k + r"=(-?[0-9A-Fa-fx]+)", l)
    return m.group(1) if m else None
armed = [l for l in sam if f(l, "this278") in ("0x0101", "0x0001")]
print("SAM total          =", len(sam))
print("SAM armed          =", len(armed))
print("armed G2 dist      =", dict(Counter(f(l, "G2") for l in armed)))
print("armed G2PASS dist  =", dict(Counter(f(l, "G2PASS") for l in armed)))
print("armed G3 dist      =", dict(Counter(f(l, "G3") for l in armed)))
print("armed G3PASS dist  =", dict(Counter(f(l, "G3PASS") for l in armed)))
print("armed this288 dist =", dict(Counter(f(l, "this288") for l in armed)))
print("armed A dist       =", dict(Counter(f(l, "A") for l in armed)))
print()
print("ALL SAM G2 dist    =", dict(Counter(f(l, "G2") for l in sam)))
print("ALL SAM G3 dist    =", dict(Counter(f(l, "G3") for l in sam)))
print("any this288=1 anywhere =", sum(1 for l in open(p, encoding='utf-8', errors='replace') if "this288=1 " in l or "this288_byte=1" in l))
