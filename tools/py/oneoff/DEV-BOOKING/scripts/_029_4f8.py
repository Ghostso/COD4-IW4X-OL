# -*- coding: utf-8 -*-
import os, re
D = r"DEV-BOOKING\_029"
for nm in sorted(os.listdir(D)):
    if not nm.startswith("snap_"):
        continue
    p = os.path.join(D, nm)
    sam = []
    for ln in open(p, encoding="utf-8", errors="replace"):
        if " SAM " not in ln:
            continue
        m = re.match(r"\[(\d\d):(\d\d):(\d\d)\.(\d+)\]", ln)
        if not m:
            continue
        t = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) + int(m.group(4))/1000.0
        d = {"t": t, "ts": "%s:%s:%s.%s" % (m.group(1), m.group(2), m.group(3), m.group(4))}
        for mm in re.finditer(r"([A-Za-z0-9_]+)=([0-9A-Fa-fx\-]+)", ln):
            d[mm.group(1)] = mm.group(2)
        sam.append(d)
    print("=== %s : %d SAM rows ===" % (nm, len(sam)))
    def spans(val):
        res, cur = [], None
        for r in sam:
            if r.get("4F8") == val:
                if cur is None: cur = [r["t"], r["t"], r["ts"], r["ts"], 1]
                else: cur[1] = r["t"]; cur[3] = r["ts"]; cur[4] += 1
            else:
                if cur: res.append(cur); cur = None
        if cur: res.append(cur)
        return res
    for v in ("1", "0"):
        sp = spans(v)
        print("   4F8=%s : %d spans, total %.3f s" % (v, len(sp), sum(x[1]-x[0] for x in sp)))
        for x in sorted(sp, key=lambda y: -(y[1]-y[0]))[:4]:
            print("      %s -> %s (%.3f s, %d)" % (x[2], x[3], x[1]-x[0], x[4]))
    # overlap check: rows where 4F4==0 AND state==1 (Path A form)
    pa = [r for r in sam if r.get("4F4") == "0x00000000" and r.get("state") == "0x00000001"]
    print("   rows with 4F4==0 and state==1 (Path A form): %d" % len(pa))
    pb = [r for r in sam if r.get("4F4") not in ("0x00000000", "0xFFFFFFFF", None) and r.get("state") == "0x00000002"]
    print("   rows with 4F4!=0 and state==2 (Path B form): %d" % len(pb))
print()
p = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\battle_srv.log"
if os.path.exists(p):
    ls = [l for l in open(p, encoding="utf-8", errors="replace") if "stat]" in l]
    print("battle RX last:", ls[-1].strip() if ls else "none")
else:
    print("battle_srv.log absent")
