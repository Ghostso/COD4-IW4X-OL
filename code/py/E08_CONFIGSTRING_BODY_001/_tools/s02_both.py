import pefile
from capstone import *
S={}
SRV=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
CLI=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
def load(P):
    d=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True)
    S={s.Name.rstrip(b"\0").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
    # first section named .text
    return d,pe,S
def off(S, rva):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=rva<v+min(vs,rs): return rp+(rva-v), nm
    return None,None
md=Cs(CS_ARCH_X86,CS_MODE_32)
for lbl,P in (("SERVER",SRV),("CLIENT-REC",CLI)):
    d,pe,S=load(P); IB=0x400000
    print("="*72); print("== %s ==" % lbl)
    for rva in (0xA0468,0xA0807,0xA0997):
        o,nm=off(S,rva)
        print("\n--- RVA 0x%X (in %s, file 0x%X) first 8 instructions:" % (rva,nm,o))
        n=0
        for ins in md.disasm(d[o:o+32], IB+rva):
            print("      %08X %-12s %s" % (ins.address,ins.mnemonic,ins.op_str)); n+=1
            if n>=8: break