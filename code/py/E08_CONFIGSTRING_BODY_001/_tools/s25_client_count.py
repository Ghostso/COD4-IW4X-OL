import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
o,_=S.off(0x1000); text=S.d[o:o+S.pe.sections[0].SizeOfRawData]
seq=list(sweep(md, text, S.IB+0x1000))
R=[(x.address-S.IB,x.mnemonic,x.op_str) for x in seq]
print("total instr:",len(R))
# does the client contain a 'cmp reg, 4' whose taken-branch then reads 2 bytes? approximate:
# find cmp x,4 ; then within 40 instr look for 'movzx ... word ptr' 
import bisect
loc=[i for i,r in enumerate(R) if r[1]=="cmp" and r[2].replace(" ","").endswith(",4")]
cand=[]
for i in loc:
    win=R[i:i+60]
    if any(m=="movzx" and "word ptr" in op for _,m,op in win):
        cand.append(R[i][0])
print("cmp x,4 followed within 60 insns by movzx word ptr:", len(cand))
print("first 20:", ["0x%X"%c for c in cand[:20]])
# and the inverse: 'movzx word ptr' shortly before 'cmp ...,4'
loc2=[i for i,r in enumerate(R) if r[1]=="movzx" and "word ptr" in r[2]]
cand2=[]
for i in loc2:
    win=R[i:i+40]
    if any(m=="cmp" and op.replace(" ","").endswith(",4") for _,m,op in win):
        cand2.append(R[i][0])
print("movzx word ptr followed within 40 insns by cmp ...,4:", len(cand2))
print("first 20:", ["0x%X"%c for c in cand2[:20]])