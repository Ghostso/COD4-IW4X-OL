# -*- coding: utf-8 -*-
import sys,pickle,bisect,collections,json
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
# recv functions from E-12
RECV=[(0x1B0430,"recvfrom",0x1B0BA1),(0x6B4DE0,"recvfrom",0x6B4E3C),(0x775AB0,"recvfrom",0x775ADE),
      (0x602430,"recv",0x602441),(0x6029A0,"recv",0x6029BE),(0x605220,"recv",0x6052AB),
      (0x775A50,"recv",0x775A6C),(0x784F60,"recv",0x784F7D),(0x78772D,"recv",0x788133)]
# direct callees with site
byfunc=collections.defaultdict(list)
for s,k,t in edges:
    f=fs(s)
    byfunc[f].append((s,k,t))
out=[]
out.append("=== 9 recv functions: 3-level downstream (call edges) ===")
TARGETS={0x3524F0:"ring-WRITER",0x352570:"ring-READER",0x350170:"demo-top-dispatch",0x3547D0:"subframe-loop",0x354100:"subframe-dispatch",0xA2660:"cfg-body",0x34FD80:"len-prefixed"}
for f,api,site in RECV:
    out.append("")
    out.append("### recv func 0x%06X (%s, IAT site 0x%06X)  boundary=[0x%06X..next)"%(f,api,site,f))
    seen={f}
    q=collections.deque([(f,0)])
    hits=[]
    while q:
        node,d=q.popleft()
        if d>=3: continue
        for s,k,t in sorted(byfunc.get(node,[])):
            tag=TARGETS.get(t)
            out.append("   L%d 0x%06X --%s@0x%06X--> 0x%06X%s"%(d,node,k,s,t,("  <<< "+tag) if tag else ""))
            if tag: hits.append((t,d+1,node,s))
            if t in seen: continue
            seen.add(t); q.append((t,d+1))
    out.append("   [targets reached within 3 levels] %s"%([(TARGETS[t],dd,hex(via)) for t,dd,via,_ in hits] or "NONE"))
    out.append("   [distinct downstream funcs] %d"%len(seen-{f}))
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_data\out_3level.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
