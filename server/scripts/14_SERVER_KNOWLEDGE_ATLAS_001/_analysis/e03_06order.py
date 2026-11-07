import pefile, struct
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
data=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
def rva2off(r):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=r<v+min(vs,rs): return rp+(r-v)
md=Cs(CS_ARCH_X86, CS_MODE_32)
print("=== E-03: snapshot writer call order, RVA 0xA4C60..0xA4E40 ===")
lo,hi=0xA4C60,0xA4E40
seg=data[rva2off(lo):rva2off(lo)+(hi-lo)]
n=0
for ins in md.disasm(seg, IB+lo):
    print("  %08X (RVA %06X) %-10s %s" % (ins.address, ins.address-IB, ins.mnemonic, ins.op_str))
    n+=1
    if n>140: break