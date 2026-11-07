import sys, bisect, collections
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=S.off(0x1000); text=S.d[o:o+S.secs[0][3]]
print("scanning client .text (%d bytes) with resync..." % len(text))
seq=[]
for ins in sweep(md, text, S.IB+0x1000): seq.append(ins)
print("decoded:", len(seq))
print()
# find 'shr reg,3' immediately followed (within 6 insns) by a 'cmp reg,[mem+4]' AND a byte load
cands=[]
for i,ins in enumerate(seq):
    if ins.mnemonic=="shr" and ins.op_str.endswith(", 3"):
        # look back 4 for mov from [r+0x10]
        back=[x for x in seq[max(0,i-5):i]]
        fwd=[x for x in seq[i:i+8]]
        hasbitpos=any(b.mnemonic=="mov" and "0x10]" in b.op_str for b in back)
        hascmp=any(f.mnemonic=="cmp" and "+ 4]" in f.op_str for f in fwd)
        if hasbitpos and hascmp:
            cands.append(ins.address-S.IB)
print("candidate bit-reader sites (shr ...,3 near [r+0x10] and cmp [r+4]): %d" % len(cands))
# cluster into functions by proximity<=0x400
clusters=[]
for a in cands:
    if clusters and a-clusters[-1][-1]<=0x400: clusters[-1].append(a)
    else: clusters.append([a])
print("clusters:", len(clusters))
for c in clusters[:30]:
    print("   around RVA 0x%X..0x%X (%d sites)" % (c[0],c[-1],len(c)))