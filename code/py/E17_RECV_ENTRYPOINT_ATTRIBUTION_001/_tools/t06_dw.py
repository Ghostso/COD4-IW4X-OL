# -*- coding: utf-8 -*-
import sys,pickle,bisect,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t): return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
print("callers 0x783F00:",[(hex(s),hex(f)) for s,k,f in callers(0x783F00)][:8])
print("callers 0x783B70:",[(hex(s),hex(f)) for s,k,f in callers(0x783B70)][:8])
print("callers 0x783DA0:",[(hex(s),hex(f)) for s,k,f in callers(0x783DA0)][:8])
print("callers 0x783B90:",[(hex(s),hex(f)) for s,k,f in callers(0x783B90)][:8])
print()
for pat in [rb"Demonware", rb"demonware", rb"DW-", rb"bdSession", rb"bdAuth", rb"bdCore"]:
    cnt=0; ex=[]
    for s in C.pe.sections:
        if s.SizeOfRawData==0: continue
        o,_=C.off(s.VirtualAddress); raw=C.d[o:o+s.SizeOfRawData]
        for m in re.finditer(re.escape(pat),raw):
            cnt+=1
            if len(ex)<3:
                b=raw[m.start():m.start()+50].split(b"\0")[0]
                ex.append((hex(C.IB+s.VirtualAddress+m.start()),b[:44]))
    print("%r count=%d %s"%(pat,cnt,ex))
