# -*- coding: utf-8 -*-
"""046_C_MATRICES.py - movement-evidence matrices from the supplied artifacts."""
import sys, os, json, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _c046 as C
X=C.X; EV=C.EV

# ---------- C2: snapshot field matrix from demo-player-fields-trace.json ----------
d=json.load(open(os.path.join(X,"reference","demo-player-fields-trace.json"),encoding="utf-8"))
print("demo-player-fields-trace.json keys:",list(d.keys()))
print("  scope:",d.get("scope"))
print("  error:",d.get("error"))
print("  reads:",len(d.get("reads",[])))
print("  origin:",d.get("origin"),"viewAngles:",d.get("viewAngles"),"cursor:",d.get("cursor"))
fields=d.get("fields",[])
print("  fields:",len(fields))
rows=[]
prev=None
for f in fields:
    cur=f.get("cursor")
    w = (cur-prev) if (prev is not None and cur is not None) else None
    rows.append((f.get("index"),f.get("offset"),f.get("codec"),cur,f.get("bit"),w,f.get("decoded")))
    prev=cur if cur is not None else prev
out=["index\toffset\tcodec\tcursor\tbit\twidth_bytes(from prev cursor)\tdecoded_value"]
for r in rows: out.append("\t".join("" if x is None else str(x) for x in r))
C.w(os.path.join(EV,"c02_snapshot_field_widths.tsv"),"\n".join(out)+"\n")

# ---------- C3: playerstate trace ----------
p=json.load(open(os.path.join(X,"reference","playerstate-motion-trace.json"),encoding="utf-8"))
keys=[k for k in p.keys() if k!="reads"]
print()
print("playerstate-motion-trace.json scalar keys:")
for k in keys:
    v=p[k]
    if isinstance(v,list) and len(v)>6: v="[list len %d]"%len(v)
    print("   %-22s %s"%(k,v))
out2=["# playerstate-motion-trace.json (authoritative/predicted motion trace)"]
for k in keys:
    out2.append("  %-22s %s"%(k, json.dumps(p[k],ensure_ascii=False)[:300]))
out2.append("  reads(bit reads observed): %d"%len(p.get("reads",[])))
C.w(os.path.join(EV,"c03_playerstate_trace.txt"),"\n".join(out2)+"\n")

# ---------- C1: usercmd vectors ----------
u=json.load(open(os.path.join(X,"reference","usercmd-native-vectors.json"),encoding="utf-8"))
print()
print("usercmd-native-vectors.json: %d cases"%len(u))
keys=sorted({c["case"] for c in u}); print("  cases:",keys)
print("  keys tested:",sorted({c["key"] for c in u}))
out3=["# usercmd-native-vectors.json summary",
      "  cases: %s"%keys,
      "  keys : %s"%sorted({c["key"] for c in u})]
for c in u[:2]:
    out3.append("  key=%s case=%s body=%s"%(c["key"],c["case"],c["body"]))
    out3.append("     baseline=%s"%c["baseline"])
    for cmd in c["commands"]: out3.append("     cmd=%s"%cmd)
C.w(os.path.join(EV,"c01_usercmd_vectors.txt"),"\n".join(out3)+"\n")
print("written c01/c02/c03")
