# -*- coding: utf-8 -*-
"""029: durations and per-cycle alignment of state=2 / 4F4=0."""
import os, re
K = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"
def parse(p):
    out = []
    for ln in open(p, encoding="utf-8", errors="replace"):
        if not ln.startswith("["):
            continue
        m = re.match(r"\[(\d\d):(\d\d):(\d\d)\.(\d+)\]\s+(\S+)", ln.strip())
        if not m:
            continue
        t = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) + int(m.group(4))/1000.0
        d = {"t": t, "ts": "%s:%s:%s.%s" % (m.group(1), m.group(2), m.group(3), m.group(4)), "kind": m.group(5)}
        for mm in re.finditer(r"([A-Za-z0-9_]+)=([0-9A-Fa-fx\-]+)", ln):
            d[mm.group(1)] = mm.group(2)
        out.append(d)
    return out
rows = parse(os.path.join(K, "accepted_state.txt"))
sam = [r for r in rows if "4F4" in r]
print("rows=%d  with-4F4=%d" % (len(rows), len(sam)))
# contiguous spans of state
def spans(key, val):
    res = []
    cur = None
    for r in sam:
        if r.get("state") == val if key == "state" else r.get("4F4") == val:
            if cur is None:
                cur = [r["t"], r["t"], r["ts"], r["ts"], 1]
            else:
                cur[1] = r["t"]; cur[3] = r["ts"]; cur[4] += 1
        else:
            if cur:
                res.append(cur); cur = None
    if cur:
        res.append(cur)
    return res
for key, val, label in (("state", "0x00000002", "state=2"), ("4F4", "0x00000000", "4F4=0")):
    sp = spans(key, val)
    tot = sum(x[1]-x[0] for x in sp)
    print()
    print("=== %s : %d spans, total %.3f s ===" % (label, len(sp), tot))
    for x in sorted(sp, key=lambda y: -(y[1]-y[0]))[:12]:
        print("   %s -> %s  (%.3f s, %d samples)" % (x[2], x[3], x[1]-x[0], x[4]))
# state=2 while 4F4 != 0 (Path B without teardown)
pb = [r for r in sam if r.get("state") == "0x00000002" and r.get("4F4") not in ("0x00000000", None, "0xFFFFFFFF")]
print()
print("=== state=2 WITH socket alive (4F4 != 0) : %d samples ===" % len(pb))
if pb:
    print("   first %s   last %s" % (pb[0]["ts"], pb[-1]["ts"]))
# per-cycle: state/4F4 around each 6/14 second
lg = os.path.join(K, "lobby_srv.log")
reqs = []
for ln in open(lg, encoding="utf-8", errors="replace"):
    if "service=6" in ln and "task=14" in ln and "\u89e3\u5bc6" in ln:
        mm = re.match(r"\[(\d\d):(\d\d):(\d\d)\]", ln)
        if mm:
            reqs.append("%s:%s:%s" % (mm.group(1), mm.group(2), mm.group(3)))
print()
print("=== 6/14 cycles: state/4F4 in a +/-1.5s window ===")
for c in reqs:
    h, mi, s = [int(x) for x in c.split(":")]
    t0 = h*3600 + mi*60 + s
    sel = [r for r in sam if t0-1.5 <= r["t"] <= t0+1.5]
    st = sorted({r.get("state") for r in sel})
    f4 = sorted({r.get("4F4") for r in sel})
    n2 = sum(1 for r in sel if r.get("state") == "0x00000002")
    print("   %s  samples=%-4d states=%-26s 4F4=%-28s state2_samples=%d" % (c, len(sel), st, f4, n2))
