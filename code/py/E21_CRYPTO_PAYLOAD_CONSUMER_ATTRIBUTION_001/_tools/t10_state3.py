import sys,struct,bisect,pickle
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E21_CRYPTO_PAYLOAD_CONSUMER_ATTRIBUTION_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"); md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_work\client_callgraph.pkl","rb")); edges=D["edges"]; prologues=D["prologues"]
def fs(r):
 i=bisect.bisect_right(prologues,r)-1; return prologues[i] if i>=0 else None
def cs(f): return sorted(set(fs(s) for s,k,t in edges if fs(t)==f))
def show(a,n):
 o,_=C.off(a); print("DISASM",hex(a));
 for ins in md.disasm(C.d[o:o+n],C.IB+a): print("%06X %-20s %s"%(ins.address-C.IB,bytes(ins.bytes).hex(),ins.mnemonic+" "+ins.op_str))
for a,n in [(0x6A9260,0xa0),(0xAAB1C0,0xe0),(0xAAB2A0,0x80)]:
 show(a,n)
for f in (0x6AACC0,0x6AAC60,0x6AC3D0,0x6AAB10,0x6AAD80):
 print("FUNC",hex(f),"callers",[hex(x) for x in cs(f)])
