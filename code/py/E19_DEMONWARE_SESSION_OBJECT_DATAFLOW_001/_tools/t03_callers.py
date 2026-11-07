import sys,pickle,bisect,collections
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t): return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
def callees(f): return sorted(set(tg for s,k,tg in edges if fs(s)==f))
print("callers of 0x6ABBC0:",[(hex(s),hex(f)) for s,k,f in callers(0x6ABBC0)])
print()
print("callees of 0x6ABBC0:",[hex(t) for t in callees(0x6ABBC0)])
print()
# 0x43A7C0 = ? (error reporting)
print("callers of 0x43A7C0 (error):",len(callers(0x43A7C0)))
print()
# who calls 0x6ABBC0's sibling 0x6ABF00?
for t in (0x6ABBC0,0x6ABB40,0x6ABF00,0x6AC000):
    cs=callers(t)
    print("  0x%06X callers=%d %s"%(t,len(cs),[(hex(s),hex(f)) for s,k,f in cs][:5]))
