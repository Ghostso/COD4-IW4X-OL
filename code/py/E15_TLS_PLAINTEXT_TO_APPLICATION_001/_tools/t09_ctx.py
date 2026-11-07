# -*- coding: utf-8 -*-
import sys,re,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
print("=== HTTP / URL strings (indicates what the TLS stack serves) ===")
for s in C.pe.sections:
    if s.SizeOfRawData==0: continue
    o,_=C.off(s.VirtualAddress); raw=C.d[o:o+s.SizeOfRawData]
    for pat in [rb"https?://[ -~]{4,60}", rb"Content-Length", rb"HTTP/1\.[01]", rb"POST [ -~]{0,30}", rb"GET [ -~]{0,30}"]:
        for m in list(re.finditer(pat,raw))[:4]:
            print("  0x%X %r"%(C.IB+s.VirtualAddress+m.start(), m.group()[:60]))
print()
print("=== function boundaries around 0x67F5F0 (scan prologues) ===")
ps=[p for p in prologues if 0x67E000<=p<=0x680000]
print("   prologues in [0x67E000,0x680000]:",[hex(p) for p in ps][:20])
print("   real func for 0x67F5F0:",hex(fs(0x67F5F0)))
print()
print("=== callers of depth-2 TLS wrappers ===")
for t in (0x607980,0x61a8a0,0x600630,0x601270,0x602240):
    cs=sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
    print("   0x%06X : %s"%(t,[(hex(s),hex(f)) for s,k,f in cs][:6]))
