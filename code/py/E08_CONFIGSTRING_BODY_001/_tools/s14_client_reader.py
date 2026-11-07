import sys; sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
# CLIENT: find reader-side primitives. E4 identified client Msg byte-read core at RVA 0x1AC1D0.
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=S.off(0x1AC1D0)
print("=== CLIENT RVA 0x1AC1D0 (Msg byte-read core, per E4) ===")
k=0
for ins in md.disasm(S.d[o:o+160], S.IB+0x1AC1D0):
    print("  %06X %-18s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=34: break
print()
# find client functions that call that core, then look for 0x04/0x06 compares among their callers
print("=== CLIENT: immediate 0x04 then 0x06 pattern scan (instruction-level, resync) ===")
import collections
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from sweep import sweep
tv,tvs,tr,trs=S.off(0x1000)
text=S.d[tr:tr+trs]
hits=[]
seq=[]
for ins in sweep(md, text, S.IB+0x1000):
    seq.append((ins.address-S.IB, ins.mnemonic, ins.op_str))
print("decoded instructions:", len(seq))
# look for functions containing 'cmp ?, 4' and 'cmp ?, 6'
c4=[]; c6=[]
for a,m,o in seq:
    if m=="cmp" and (", 4" in o or "4, " in o): c4.append(a)
    if m=="cmp" and (", 6" in o or "6, " in o): c6.append(a)
print("cmp ...,4 count=%d ; cmp ...,6 count=%d" % (len(c4),len(c6)))
import bisect
near=[]
for a in c4:
    i=bisect.bisect_left(c6,a)
    for j in (i-1,i,i+1):
        if 0<=j<len(c6) and 0<=c6[j]-a<=0x400: near.append((a,c6[j],c6[j]-a))
print("pairs (cmp4 then cmp6 within 0x400): %d" % len(near))
for x in near[:25]: print("   cmp4@0x%X cmp6@0x%X delta=0x%X" % x)