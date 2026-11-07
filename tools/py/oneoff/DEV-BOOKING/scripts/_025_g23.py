# -*- coding: utf-8 -*-
"""025: extract G2/G3 during the booking-armed window (read-only)."""
import os, re
from collections import Counter
D = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"
p = os.path.join(D, "accepted_state.txt")
rows = []
for ln in open(p, encoding="utf-8", errors="replace"):
    if "SAM " not in ln:
        continue
    d = {}
    ts = ln[1:ln.index("]")] if "]" in ln else ""
    for m in re.finditer(r"([A-Za-z0-9_]+)=([0-9A-Fa-fx\-]+)", ln):
        d[m.group(1)] = m.group(2)
    d["ts"] = ts
    rows.append(d)
print("SAM rows =", len(rows))
def i32(s):
    try: return int(s, 16) if s.startswith("0x") else int(s)
    except Exception: return None
armed = [r for r in rows if (i32(r.get("this278", "0")) or 0) & 0xFF]
print("armed rows (this278 low byte != 0) =", len(armed))
print("  this278 values:", dict(Counter(r.get("this278") for r in armed)))
print("  G2 values     :", dict(Counter(r.get("G2") for r in armed)))
print("  G2PASS        :", dict(Counter(r.get("G2PASS") for r in armed)))
print("  G3 values     :", dict(Counter(r.get("G3") for r in armed)))
print("  G3PASS        :", dict(Counter(r.get("G3PASS") for r in armed)))
print()
print("--- armed rows (first 40) ---")
for r in armed[:40]:
    print("   %s G2=%s G2s=%s G2PASS=%s G3=%s G3PASS=%s this278=%s this288=%s A=%s B=%s" %
          (r.get("ts"), r.get("G2"), r.get("G2s"), r.get("G2PASS"), r.get("G3"),
           r.get("G3PASS"), r.get("this278"), r.get("this288"), r.get("A"), r.get("B")))
print()
print("--- G2 distribution over ALL rows ---")
print(dict(Counter(r.get("G2") for r in rows).most_common(8)))
print("--- G3 distribution over ALL rows (top) ---")
print(dict(Counter(r.get("G3") for r in rows).most_common(8)))
