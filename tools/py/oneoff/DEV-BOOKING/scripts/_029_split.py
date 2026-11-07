# -*- coding: utf-8 -*-
"""029: split Path A (4F4=0 teardown) vs Path B (state=2 inert tick)."""
import os, re
from collections import Counter
K = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"
p = os.path.join(K, "accepted_state.txt")
rows = []
for ln in open(p, encoding="utf-8", errors="replace"):
    if not ln.startswith("["):
        continue
    m = re.match(r"\[(\d\d):(\d\d):(\d\d)(?:\.(\d+))?\]\s+(\S+)", ln.strip())
    if not m:
        continue
    t = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) + int((m.group(4) or "0").ljust(3,"0")[:3])/1000.0
    d = {"t": t, "ts": "%s:%s:%s.%s" % (m.group(1), m.group(2), m.group(3), (m.group(4) or "000")),
         "kind": m.group(5)}
    for mm in re.finditer(r"([A-Za-z0-9_]+)=([0-9A-Fa-fx\-]+)", ln):
        d[mm.group(1)] = mm.group(2)
    rows.append(d)
print("rows =", len(rows), " kinds =", dict(Counter(r["kind"] for r in rows)))
def i(s):
    try:
        return int(s, 16) if s and s.startswith("0x") else (int(s) if s else None)
    except Exception:
        return None
print()
print("=== 4F4 distribution ===")
print(dict(Counter(r.get("4F4") for r in rows if "4F4" in r).most_common(8)))
print("=== state distribution ===")
print(dict(Counter(r.get("state") for r in rows if "state" in r).most_common(8)))
print("=== 4F8 distribution ===")
print(dict(Counter(r.get("4F8") for r in rows if "4F8" in r).most_common(8)))
print()
print("=== transitions of (4F4, 4F8, state) ===")
prev = None
for r in rows:
    key = (r.get("4F4"), r.get("4F8"), r.get("state"))
    if key != prev and key[0] is not None:
        print("   %s %-4s 4F4=%-10s 4F8=%-3s state=%-10s this278=%-6s this288=%s t_5E8=%s" %
              (r["ts"], r["kind"], key[0], key[1], key[2], r.get("this278","-"), r.get("this288","-"), r.get("t_5E8","-")))
        prev = key
