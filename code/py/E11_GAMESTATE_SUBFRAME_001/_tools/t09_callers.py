# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fstart(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t):
    return sorted(set((s,k,fstart(s)) for s,k,tg in edges if tg==t))
def callees(f):
    return sorted(set((s,k,tg) for s,k,tg in edges if fstart(s)==f))
for a in (0x350170,0x3547D0,0x354100,0x34FD80,0x350040,0x3512A0,0x352F80,0xA2660,0x751C70,0x751D00,0x753A40):
    print("0x%06X callers:"%a)
    for s,k,f in callers(a): print("     site 0x%06X %s in 0x%06X"%(s,k,f))
    if not callers(a): print("     (none)")
print()
print("0x350170 callees:")
for s,k,t in callees(0x350170): print("     0x%06X %s -> 0x%06X"%(s,k,t))
print()
print("0x3547D0 callees:")
for s,k,t in callees(0x3547D0): print("     0x%06X %s -> 0x%06X"%(s,k,t))
