import sys,pickle,bisect,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t):
    return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
print("=== EXE_ERR strings 0xCD6000-0xCD6600 ===")
o,_=C.off(0xCD6000)
raw=C.d[o:o+0x600]
for m in re.finditer(rb"EXE_[A-Z_]+", raw):
    va=C.IB+0xCD6000+m.start()
    b=raw[m.start():m.start()+80].split(b"\0")[0]
    print("   0x%X %r"%(va,b.decode("latin-1")))
print()
for t in (0x9CFE0,0x8F1D0,0x1A9060,0x1A9760,0x356580,0x34E7C0):
    print("callers of 0x%06X:"%t)
    cs=callers(t)
    if not cs: print("     (none in .text direct)")
    for s,k,f in cs: print("     site 0x%06X %s in 0x%06X"%(s,k,f))
