# -*- coding: utf-8 -*-
import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
# find demo/replay related strings
pats=[b"demo",b"Demo",b"DEMO",b"replay",b"Replay",b".dm_",b"record"]
hits=[]
for sec in C.pe.sections:
    if sec.SizeOfRawData==0: continue
    o,_=C.off(sec.VirtualAddress)
    raw=C.d[o:o+sec.SizeOfRawData]
    for pat in pats:
        for m in re.finditer(re.escape(pat),raw):
            va=C.IB+sec.VirtualAddress+m.start()
            b=raw[m.start():m.start()+64]
            s=b.split(b"\0")[0]
            hits.append((va,pat.decode(),s))
seen=set(); out=[]
for va,p,s in sorted(hits):
    if va in seen: continue
    seen.add(va); out.append((va,p,s))
print("total",len(out))
for va,p,s in out[:120]:
    try: txt=s.decode("latin-1")
    except: txt=repr(s)
    print("  0x%X  %-7s %r"%(va,p,txt[:70]))
