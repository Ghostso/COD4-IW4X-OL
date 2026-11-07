import pefile, json
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
d=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={s.Name.rstrip(b"\0").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
def off(r):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=r<v+min(vs,rs): return rp+(r-v)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
lo,hi=0xA0468,0xA0A60
seg=d[off(lo):off(lo)+(hi-lo)]
print("=== SERVER _CODOL2697_WriteConfigstrings  RVA 0xA0468 .. 0xA0A60 ===")
n=0
for ins in md.disasm(seg, IB+lo):
    mark=""
    if ins.address-IB in (0xA07F8,0xA0807,0xA0997): mark="   <== KEY"
    print("  %08X %-22s %-28s%s" % (ins.address, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str, mark))
    n+=1
    if n>400: print("   ...truncated"); break