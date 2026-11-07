# -*- coding: utf-8 -*-
import sys,struct,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def ptrscan(va):
    tv=0x400000+va; out=[]
    for s in C.pe.sections:
        if s.SizeOfRawData==0: continue
        o,_=C.off(s.VirtualAddress)
        raw=C.d[o:o+s.SizeOfRawData]
        for i in range(0,max(0,len(raw)-3)):
            if struct.unpack_from("<I",raw,i)[0]==tv:
                out.append((s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress+i))
    return out
for va in (0x34E7C0,0x34E300,0x34E950,0x3519F0,0x351A10,0x351710,0x3518C0,0x3512A0,0x356580,0x8F1D0,0x350170,0x3547D0,0x354100,0xA2660):
    r=ptrscan(va)
    print("0x%06X dataptr=%d %s"%(va,len(r),["0x%X"%x[1] for x in r[:5]]))
print()
for t in (0x3519F0,0x351A10,0x34E7C0,0x3512A0):
    cs=sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
    print("direct callers of 0x%06X: %s"%(t,[(hex(s),k,hex(f)) for s,k,f in cs]))
