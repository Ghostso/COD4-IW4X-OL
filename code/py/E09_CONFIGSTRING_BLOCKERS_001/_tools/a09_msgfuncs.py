import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
# Enumerate prologues in Msg module and classify each by memory ops
o,_=C.off(0x1AB800)
size=0x1A000
cur=None; body=[]
funcs={}
for ins in md.disasm(C.d[o:o+size], C.IB+0x1AB800):
    rva=ins.address-C.IB
    if ins.mnemonic=="push" and ins.op_str=="ebp" and cur is not None:
        funcs[cur]=body; body=[]
        cur=rva
    elif cur is None and ins.mnemonic=="push" and ins.op_str=="ebp":
        cur=rva
    body.append((ins.mnemonic,ins.op_str))
if cur is not None: funcs[cur]=body
print("prologues in 0x1AB800..0x%X: %d" % (0x1AB800+size,len(funcs)))
for rva,insns in sorted(funcs.items()):
    txt=" ".join("%s %s"%(m,o) for m,o in insns)
    n_and7 = sum(1 for m,o in insns if m=="and" and o.replace(" ","").endswith(",7"))
    n_shr3 = sum(1 for m,o in insns if m=="shr" and o.replace(" ","").endswith(",3"))
    w_bits = ("byte ptr [eax], cl" in txt)
    r_bits = ("test" in txt and "byte ptr" in txt and (n_and7>0 or n_shr3>0))
    nsz = sum(1 for m,o in insns if m=="movzx" and "byte ptr" in o)
    if n_and7 or n_shr3 or w_bits or nsz>3:
        print("  0x%06X  insns=%-3d and7=%-2d shr3=%-2d movzx_byte=%-2d writebit=%-5s readbit~=%-5s" % (
            rva,len(insns),n_and7,n_shr3,nsz,w_bits,r_bits))