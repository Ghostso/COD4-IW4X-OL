# -*- coding: utf-8 -*-
"""029: snapshot the probe file and align state/4F4 with each accepted push."""
import os, re, shutil, time
K = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"
D = r"DEV-BOOKING\_029"
os.makedirs(D, exist_ok=True)
src = os.path.join(K, "accepted_state.txt")
tag = time.strftime("%H%M%S")
dst = os.path.join(D, "snap_%s.txt" % tag)
if os.path.exists(src):
    shutil.copyfile(src, dst)
print("snapshot ->", dst, os.path.getsize(dst), "B")
rows = []
for ln in open(dst, encoding="utf-8", errors="replace"):
    if not ln.startswith("["):
        continue
    m = re.match(r"\[(\d\d):(\d\d):(\d\d)\.(\d+)\]\s+(\S+)", ln.strip())
    if not m:
        continue
    t = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) + int(m.group(4))/1000.0
    d = {"t": t, "ts": "%s:%s:%s.%s" % (m.group(1), m.group(2), m.group(3), m.group(4)), "kind": m.group(5)}
    for mm in re.finditer(r"([A-Za-z0-9_]+)=([0-9A-Fa-fx\-]+)", ln):
        d[mm.group(1)] = mm.group(2)
    rows.append(d)
sam = [r for r in rows if "4F4" in r]
print("rows=%d with4F4=%d  first=%s last=%s" % (len(rows), len(sam), sam[0]["ts"] if sam else "-", sam[-1]["ts"] if sam else "-"))
def spans(key, val):
    res, cur = [], None
    for r in sam:
        ok = (r.get("state") == val) if key == "state" else (r.get("4F4") == val)
        if ok:
            if cur is None: cur = [r["t"], r["t"], r["ts"], r["ts"], 1]
            else: cur[1] = r["t"]; cur[3] = r["ts"]; cur[4] += 1
        else:
            if cur: res.append(cur); cur = None
    if cur: res.append(cur)
    return res
for key, val, lab in (("state", "0x00000002", "state=2"), ("state", "0x00000001", "state=1"),
                      ("state", "0x00000000", "state=0"), ("4F4", "0x00000000", "4F4=0")):
    sp = spans(key, val)
    print("\n=== %s : %d spans, total %.3f s ===" % (lab, len(sp), sum(x[1]-x[0] for x in sp)))
    for x in sorted(sp, key=lambda y: -(y[1]-y[0]))[:6]:
        print("   %s -> %s (%.3f s, %d samples)" % (x[2], x[3], x[1]-x[0], x[4]))
print("\n=== accepted pushes (server log) vs state/4F4 ===")
lg = os.path.join(K, "lobby_srv.log")
pushed = []
for ln in open(lg, encoding="utf-8", errors="replace"):
    if "push 'mmbook accepted'" in ln:
        m = re.match(r"\[(\d\d):(\d\d):(\d\d)\]", ln)
        if m: pushed.append("%s:%s:%s" % (m.group(1), m.group(2), m.group(3)))
print("   pushes seen:", pushed)
for c in pushed:
    h, mi, s = [int(x) for x in c.split(":")]
    t0 = h*3600 + mi*60 + s
    sel = [r for r in sam if t0-2 <= r["t"] <= t0+2]
    print("   %s : %d samples; states=%s 4F4=%s" % (c, len(sel),
          sorted({r.get("state") for r in sel}), sorted({r.get("4F4") for r in sel})))
