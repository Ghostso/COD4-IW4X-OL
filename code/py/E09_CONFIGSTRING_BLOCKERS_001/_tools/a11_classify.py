import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
# classify each function in 0x1AC380..0x1AC720 by read vs write bit signature
o,_=C.off(0x1AC380)
cur=None; funcs={}
for ins in md.disasm(C.d[o:o+0x500], C.IB+0x1AC380):
    rva=ins.address-C.IB
    if ins.mnemonic=="push" and ins.op_str=="ebp":
        cur=rva; funcs[cur]=[]
    if cur is not None: funcs[cur].append((ins.mnemonic,ins.op_str,bytes(ins.bytes).hex()))
for rva,insns in sorted(funcs.items()):
    txt=" ".join("%s %s"%(m,o) for m,o,_ in insns)
    write = ("byte ptr [eax], cl" in txt) or ("or byte ptr" in txt and ", cl" in txt)
    readish = ("test" in txt and any("byte ptr [eax" in o or "byte ptr [eax +" in o for m,o,_ in insns))
    and7 = sum(1 for m,o,_ in insns if m=="and" and o.replace(" ","").endswith(",7"))
    shr3 = sum(1 for m,o,_ in insns if m=="shr" and o.replace(" ","").endswith(",3"))
    shr_cl = sum(1 for m,o,_ in insns if m=="shr" and o.endswith(", cl"))
    print("  0x%06X  n=%-3d write=%-5s readish=%-5s and7=%d shr3=%d shr_cl=%d" % (rva,len(insns),write,readish,and7,shr3,shr_cl))