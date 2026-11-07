import sys, collections
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=S.off(0x1000); text=S.d[o:o+S.pe.sections[0].SizeOfRawData]
seq=list(sweep(md, text, S.IB+0x1000))
c=collections.Counter()
shr3=[]; and7=[]; shl=[]
for ins in seq:
    m=ins.mnemonic; op=ins.op_str.replace(" ","")
    c[m]+=1
    if m=="shr" and op.endswith(",3"): shr3.append(ins.address-S.IB)
    if m=="and" and op.endswith(",7"): and7.append(ins.address-S.IB)
    if m=="shl": shl.append(ins.address-S.IB)
print("total instr:",len(seq))
print("top mnemonics:", c.most_common(15))
print("shr ...,3 : %d" % len(shr3))
print("and ...,7 : %d" % len(and7))
print("shl       : %d" % len(shl))
print()
print("first 15 'shr reg,3':", ["0x%X"%x for x in shr3[:15]])
print("first 15 'and reg,7':", ["0x%X"%x for x in and7[:15]])