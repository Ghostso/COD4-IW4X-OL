# -*- coding: utf-8 -*-
import os, csv, json, re
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL"
OUT=os.path.join(ROOT,"CODOL-DEMONWARE-BUNDLE-001")
d=json.load(open(os.path.join(OUT,"_register_raw.json"),encoding="utf-8"))
rows=d["rows"]
from collections import defaultdict
by=defaultdict(lambda:[0,0])
for r in rows:
    if r["impact"]=="I4":
        t=r["task"] or "XVAL-02(E-15)"
        by[t][0]+=1; by[t][1]+=r["weight"]
tot=0
for k in sorted(by):
    print("%-26s I4 n=%2d weight=%3d"%(k,by[k][0],by[k][1])); tot+=by[k][1]
print("TOTAL I4 weight",tot)
print()
# which Q are I4 in XVAL-02 block
xs=[r["q"] for r in rows if r["impact"]=="I4" and (r["task"] or "").startswith("E-15")]
print("XVAL-02 I4:",xs,len(xs))
print()
# per-delta I4 counts
for task in ("E-21","E-22","E-23","E-24","E-25","E-26","E-27","PEER-REUSE-AUDIT-001","CODEC-KEYFLOW-001"):
    qs=[r["q"] for r in rows if r["task"]==task and r["impact"]=="I4"]
    print("%-24s I4=%2d w=%2d %s"%(task,len(qs),8*len(qs),qs))
