import sys,struct,bisect,pickle,collections
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E21_CRYPTO_PAYLOAD_CONSUMER_ATTRIBUTION_001\_tools")
from pe_helper import PE
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(P); md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(f): return sorted(set(fs(s) for s,k,t in edges if fs(t)==f))
def callees(f): return sorted(set(t for s,k,t in edges if fs(s)==f))
# all callers of 0x6A84E0, with call-site context and call targets
cs=[(s,t) for s,k,t in edges if fs(t)==0x6A84E0]
print("CALLSITES",len(cs))
for s,t in cs[:80]: print(hex(s),hex(fs(s)),"->",hex(t))
# method direct callers from graph
for m in (0x6A8270,0x6A8370,0x6A83C0,0x6A82E0,0x6A88C0,0x6A8720):
    print("METHOD",hex(m),"callers",[hex(x) for x in callers(m)],"callees",[hex(x) for x in callees(m)])
# find instruction references to vtable rva 0x85B0A4 / VA 0xC5B0A4 and neighbors
needles=[0x85B0A4,0xC5B0A4,0x85B0E0,0xC5B0E0,0x85B0EC,0xC5B0EC]
# targeted disasm around callers and vtable-writing functions
def context(a,b,tag):
    print("CONTEXT",tag,hex(a),hex(b))
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
        if ins.mnemonic in ("call","jmp") or "0x85b0a4" in ins.op_str.lower() or "0xc5b0a4" in ins.op_str.lower() or "0x85b0e0" in ins.op_str.lower() or "0xc5b0e0" in ins.op_str.lower():
            print("  %06X %s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
for s,t in cs[:40]:
    context(max(0,s-24),s+16,"caller "+hex(fs(s)))
# search for object field pointer stores +0xb0/+0xb4 near 0x6A9
print("FIELD STORES 0xB0/0xB4")
pat=[b"\x89\x8e\xb0\x00\x00\x00",b"\x89\x9e\xb0\x00\x00\x00",b"\x89\xbe\xb0\x00\x00\x00",b"\x89\x8e\xb4\x00\x00\x00",b"\x89\x9e\xb4\x00\x00\x00",b"\x89\xbe\xb4\x00\x00\x00"]
for p in pat:
    i=0
    while True:
        j=C.d.find(p,i)
        if j<0: break
        rv=None
        for nm,va,vs,rp,rs in C.secs:
            if rp<=j<rp+rs: rv=va+j-rp; break
        print(" ",p.hex(),hex(j),hex(rv) if rv else None)
        i=j+1
