import pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
d=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={s.Name.rstrip(b"\0").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
def off(r):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=r<v+min(vs,rs): return rp+(r-v)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def show(rva, n=28, label=""):
    print("=== %s  RVA 0x%X ===" % (label,rva))
    k=0
    for ins in md.disasm(d[off(rva):off(rva)+160], IB+rva):
        print("  %08X %-20s %-26s" % (ins.address, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()
show(0x499551, 14, "prim A (used for 0x04 and 0x06 - single immediate)")
show(0x499566, 14, "prim B (used for count1)")
show(0x499590, 20, "prim C (msg,value,bitcount) -> WriteBits?")
show(0x499651, 16, "prim D (used after index write for array1)")
show(0x4A0400, 26, "index writer (called before array1/array3 entry)")