# -*- coding: utf-8 -*-
"""a22: search for game-protocol signature strings."""
import sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
pats=["netchan","svc_","clc_","configstring","gamestate","snapshot","reliable",
      "ServerCommand","servercommand","clientcommand","challenge","connectResponse",
      "baseline","netfield","delta_","svs_","cls_","CS_","net_","NET_","packet"]
pat=re.compile(rb"[ -~]{4,}")
found={}
for m in pat.finditer(C._img):
    st=m.group().decode("latin1")
    for p in pats:
        if p.lower() in st.lower():
            found.setdefault(p,[]).append((m.start(),st)); break
for p in pats:
    v=found.get(p,[])
    print("### %-16s : %d hits"%(p,len(v)))
    for a,st in v[:12]: print("      0x%08X %r"%(a,st))
