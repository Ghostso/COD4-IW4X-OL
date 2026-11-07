import sys, bisect, collections
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
o,_=S.off(0x1000); text=S.d[o:o+S.pe.sections[0].SizeOfRawData]
seq=list(sweep(md, text, S.IB+0x1000))
R=[(x.address-S.IB, x.mnemonic, x.op_str, bytes(x.bytes)) for x in seq]
print("decoded",len(R))
# 1) bit-reader primitive signature: and r,7 immediately followed (<=6 insn) by shr r,3
pairs=[]
for i in range(len(R)-7):
    a=R[i]; 
    if a[1]=="and" and a[2].replace(" ","").endswith(",7"):
        for j in range(i+1,min(i+6,len(R))):
            if R[j][1]=="shr" and R[j][2].replace(" ","").endswith(",3"):
                pairs.append((a[0],R[j][0])); break
print("client bit-reader primitive pairs (and r,7 ... shr r,3):", len(pairs))
# 2) cmp x, 4 and cmp x, 6 instruction-level
c4=[r[0] for r in R if r[1]=="cmp" and r[2].replace(" ","").endswith(",4")]
c6=[r[0] for r in R if r[1]=="cmp" and r[2].replace(" ","").endswith(",6")]
print("cmp x,4 =",len(c4)," cmp x,6 =",len(c6))
# 3) functions containing a reader pair AND a cmp4 AND a cmp6 within 0x800
def near(lst,a,win):
    i=bisect.bisect_left(lst,a); out=[]
    for j in (i-1,i,i+1,... ):
        pass
    return out
hits=[]
for pa,pb in pairs:
    n4=any(abs(x-pa)<=0x800 for x in c4)
    n6=any(abs(x-pa)<=0x800 for x in c6)
    if n4 and n6: hits.append((pa,pb))
print("reader pairs within 0x800 of BOTH cmp4 and cmp6:", len(hits))
for h in hits[:40]: print("   reader@0x%X (shr@0x%X)" % h)