import pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
data=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
def rva2off(r):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=r<v+min(vs,rs): return rp+(r-v)
md=Cs(CS_ARCH_X86, CS_MODE_32)
print("=== E-05b: ReadRegistration tail 0xA3F69..0xA43F0 (scan for 0x6408 / 0xC814 / crc) ===")
lo,hi=0xA3F69,0xA43F0
seg=data[rva2off(lo):rva2off(lo)+(hi-lo)]
n=0
for ins in md.disasm(seg, IB+lo):
    s=ins.op_str
    if any(k in s for k in ["0x6418","0x6410","0x6408","0xc814","0xc820","call"]) or ins.mnemonic in ("mov","cmp","test") and "0x641" in s:
        print("  %08X %-10s %s" % (ins.address, ins.mnemonic, s))
        n+=1
    if n>70: break