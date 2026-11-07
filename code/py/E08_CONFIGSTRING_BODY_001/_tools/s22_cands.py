import sys, bisect
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
def show(start,n,label):
    print("=== %s  from RVA 0x%X ===" % (label,start))
    o,_=S.off(start); k=0
    for ins in md.disasm(S.d[o:o+400], S.IB+start):
        print("   %06X %-18s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()
# back up to a prologue before each candidate
for rva,label in ((0x510200,"cand A 0x510233"),(0x5F0120,"cand B 0x5F0175"),(0x1A0700,"cand C 0x1A07E7")):
    # find 'push ebp; mov ebp,esp' before rva
    o,_=S.off(rva)
    win=S.d[o-0x200:o+0x120]
    idx=win.rfind(b"\x55\x8b\xec")
    base=0 if idx<0 else idx
    show((rva-0x200+base) if idx>=0 else rva, 34, label)