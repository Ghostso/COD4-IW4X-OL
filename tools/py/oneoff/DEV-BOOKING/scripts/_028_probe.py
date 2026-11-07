# -*- coding: utf-8 -*-
import os, re
K = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"
p = os.path.join(K, "accepted_state.txt")
rows = []
for ln in open(p, encoding="utf-8", errors="replace"):
    m = re.match(r"\[?(\d\d):(\d\d):(\d\d)(?:\.(\d+))?\]?\s+(\S+)", ln.strip()) if ln.startswith("[") else None
    if not m:
        continue
    t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    ms = int((m.group(4) or "0").ljust(3, "0")[:3])
    d = {"t": t, "ms": ms, "ts": "%s:%s:%s.%03d" % (m.group(1), m.group(2), m.group(3), ms), "kind": m.group(5)}
    for mm in re.finditer(r"([A-Za-z0-9_]+)=([0-9A-Fa-fx\-]+)", ln):
        d[mm.group(1)] = mm.group(2)
    rows.append(d)
print("probe rows parsed:", len(rows))
cycles = ["23:05:59", "23:07:47", "23:07:49", "23:07:52", "23:07:54", "23:07:59",
          "23:09:09", "23:09:12", "23:09:19", "23:09:24", "23:09:34"]
for c in cycles:
    h, mi, s = [int(x) for x in c.split(":")]
    t0 = h * 3600 + mi * 60 + s
    sel = [r for r in rows if t0 - 1 <= r["t"] <= t0 + 1]
    kinds = {}
    for r in sel:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print("\n=== cycle %s : %d probe rows in +/-1s %s ===" % (c, len(sel), kinds))
    show = [r for r in sel if r["kind"] in ("CHG", "INI", "SAM")]
    if len(show) > 14:
        show = show[:6] + show[-8:]
    for r in show:
        print("   %s %-4s t_C8=%s t_644=%s t_5E8=%s this278=%s this288=%s A=%s B=%s net4F8=%s" %
              (r["ts"], r["kind"], r.get("t_C8", "-"), r.get("t_644", "-"), r.get("t_5E8", "-"),
               r.get("this278", "-"), r.get("this288", r.get("this288_byte", "-")),
               r.get("A", "-"), r.get("B", "-"), r.get("net4F8", "-")))
