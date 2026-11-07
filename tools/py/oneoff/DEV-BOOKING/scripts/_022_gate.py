# -*- coding: utf-8 -*-
"""022: parse accepted-state probe logs -> field distributions + transitions (read-only)."""
import os, re
from collections import Counter, OrderedDict

D = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"
FIELDS = ["matching", "this288_byte", "this288_word", "this278", "this283", "this1C",
          "flag849B61C", "flag", "net", "net4F8", "trans", "t_C8", "t_644", "t_5E8", "dw", "A", "B"]

def parse(path):
    rows = []
    for ln in open(path, encoding="utf-8", errors="replace"):
        if not ln.startswith("["):
            continue
        ts = ln[1:ln.index("]")] if "]" in ln else ""
        tag = ln.split("]", 1)[1].strip().split(" ")[0] if "]" in ln else ""
        d = {"ts": ts, "tag": tag}
        for m in re.finditer(r"([A-Za-z0-9_]+)=([0-9A-Fa-fx\-]+)", ln):
            d[m.group(1)] = m.group(2)
        rows.append(d)
    return rows

for name in ["accepted_state_019test.txt", "accepted_state.txt.test019_20261008_201410",
             "accepted_state.txt"]:
    p = os.path.join(D, name)
    if not os.path.exists(p):
        continue
    rows = parse(p)
    print("=" * 92)
    print("%s : %d rows" % (name, len(rows)))
    for f in ["this288_byte", "this278", "A", "B", "flag849B61C", "t_5E8", "t_C8"]:
        c = Counter(r.get(f, "-") for r in rows)
        print("  %-14s %s" % (f, dict(list(c.most_common(6)))))
    lived = [r for r in rows if r.get("matching", "0x00000000") not in ("0x00000000",)]
    print("  rows with matching!=0 : %d" % len(lived))
    prev = None
    print("  --- A/B transitions (matching!=0) ---")
    shown = 0
    for r in lived:
        key = (r.get("A"), r.get("B"), r.get("this278"), r.get("this288_byte"))
        if key != prev:
            print("     %s %s A=%s B=%s this278=%s this288=%s flag=%s t_5E8=%s" %
                  (r.get("ts"), r.get("tag"), r.get("A"), r.get("B"), r.get("this278"),
                   r.get("this288_byte"), r.get("flag849B61C", r.get("flag", "-")), r.get("t_5E8")))
            prev = key
            shown += 1
            if shown > 26:
                print("     ... (truncated)")
                break
