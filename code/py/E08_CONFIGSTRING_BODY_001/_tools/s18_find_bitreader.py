import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=S.off(0x1000)
size=S.pe.sections[0].SizeOfRawData
text=S.d[o:o+size]
print("client .text raw size = 0x%X (%d)" % (size,size))
seq=[]
for ins in sweep(md, text, S.IB+0x1000): seq.append(ins)
print("decoded:", len(seq))
print()
cands=[]
for i,ins in enumerate(seq):
    if ins.mnemonic=="shr" and ins.op_str.strip().endswith(",3"):
        back=seq[max(0,i-6):i]
        fwd=seq[i:i+9]
        hasbitpos=any(b.mnemonic=="mov" and "0x10]" in b.op_str for b in back)
        hascmp=any(f.mnemonic=="cmp" and "+ 4]" in f.op_str for f in fwd)
        if hasbitpos and hascmp: cands.append(ins.address-S.IB)
print("candidate bit-reader sites:", len(cands))
clusters=[]
for a in cands:
    if clusters and a-clusters[-1][-1]<=0x600: clusters[-1].append(a)
    else: clusters.append([a])
print("clusters:", len(clusters))
for c in clusters[:25]:
    print("   RVA 0x%X .. 0x%X  sites=%d" % (c[0],c[-1],len(c)))