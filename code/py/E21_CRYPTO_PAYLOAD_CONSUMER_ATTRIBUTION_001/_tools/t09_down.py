import sys,bisect,pickle
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E21_CRYPTO_PAYLOAD_CONSUMER_ATTRIBUTION_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"); md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_work\client_callgraph.pkl","rb")); edges=D["edges"]; prologues=D["prologues"]
def fs(r):
 i=bisect.bisect_right(prologues,r)-1; return prologues[i] if i>=0 else None
def cs(f): return sorted(set(fs(s) for s,k,t in edges if fs(t)==f))
def cl(f): return sorted(set(t for s,k,t in edges if fs(s)==f))
def show(a,n,tag):
 print("="*72); print(tag,hex(a),hex(a+n)); print("-"*72)
 o,_=C.off(a)
 for ins in md.disasm(C.d[o:o+n],C.IB+a): print("%06X %-22s %s %s"%(ins.address-C.IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
for a,n,t in [(0xAAB260,0x140,"0xAAB260"),(0xAAB310,0x140,"0xAAB310"),(0xA85AD0,0x100,"0xA85AD0"),(0xA85640,0x100,"0xA85640"),(0xAABE60,0x120,"0xAABE60"),(0xAA9570,0x120,"0xAA9570")]:
 show(a,n,t)
for f in (0xAAB260,0xAAB310,0xA85AD0,0xA85640,0xAABE60,0xAA9570):
 print("FUNC",hex(f),"callers",[hex(x) for x in cs(f)],"callees",[hex(x) for x in cl(f)])
