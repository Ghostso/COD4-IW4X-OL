# -*- coding: utf-8 -*-
import sys,pickle,bisect,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t): return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
def datap(va):
    tv=0x400000+va; out=[]
    for s in C.pe.sections:
        if s.SizeOfRawData==0: continue
        o,_=C.off(s.VirtualAddress); raw=C.d[o:o+s.SizeOfRawData]
        for i in range(0,max(0,len(raw)-3)):
            if struct.unpack_from("<I",raw,i)[0]==tv:
                out.append((s.Name.rstrip(b'\0').decode(errors='replace'),s.VirtualAddress+i))
    return out
for t in (0x6B4DE0,0x784F60):
    print("=== 0x%06X ==="%t)
    for s,k,f in callers(t): print("   call 0x%06X in 0x%06X"%(s,f))
    print("   dataptr:",[(n,hex(r)) for n,r in datap(t)])
    print()
