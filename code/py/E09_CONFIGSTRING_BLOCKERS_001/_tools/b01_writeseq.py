import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32)
LO,HI=0xA04E3,0xA0A80
o,_=S.off(LO)
seq=[]
for ins in md.disasm(S.d[o:o+(HI-LO)], S.IB+LO):
    seq.append((ins.address-S.IB, ins.mnemonic, ins.op_str, bytes(ins.bytes)))
print("instructions in body:", len(seq))
# primitives
PRIM={0x99551:"WriteByte", 0x99566:"WriteShort", 0x9957B:"WriteLong",
      0x99590:"WriteBits", 0x9949B:"WriteData", 0xA0400:"WriteIndexDelta", 0x99651:"WriteLenStr"}
def target(op):
    if op.startswith("0x"):
        try: return int(op,16)-S.IB
        except: return None
    return None
print()
print("=== primitive call sites in order (with the 3 stack args set just before) ===")
for i,(rva,m,op,b) in enumerate(seq):
    if m=="call":
        t=target(op)
        if t in PRIM:
            # gather last 3 'mov dword [esp+N], X' or pushes before
            args=[]
            for j in range(max(0,i-14),i):
                rr,mm,oo,bb=seq[j]
                if mm=="mov" and oo.startswith("dword ptr [esp"):
                    args.append((rr,oo))
                elif mm=="push":
                    args.append((rr,"push "+oo))
            print("  0x%06X  call %-8s <- %s" % (rva,PRIM[t], "; ".join("%s:%s"%(hex(a),s) for a,s in args[-4:])))