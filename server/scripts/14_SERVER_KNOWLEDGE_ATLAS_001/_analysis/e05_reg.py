import pefile, struct
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
data=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
def rva2off(r):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=r<v+min(vs,rs): return rp+(r-v)
print("=== E-05: registration format strings ===")
for tok in [b"codol2697-registration", b"withheld", b"verified client registration"]:
    c=0;o=0
    while True:
        i=data.find(tok,o)
        if i<0: break
        rva=None
        for nm,(v,vs,rp,rs) in S.items():
            if rp<=i<rp+rs: rva=v+(i-rp)
        # print the string
        end=data.find(b"\x00",i)
        print("  VA 0x%08X RVA %s : %r" % (IB+rva, ("0x%X"%rva) if rva else "?", data[i:min(end,i+120)].decode("latin1")))
        c+=1;o=i+1
        if c>6: break
print()
print("=== E-05: disasm _CODOL2697_ReadRegistration head (RVA 0xA3EA0) ===")
md=Cs(CS_ARCH_X86, CS_MODE_32)
r=0xA3EA0; seg=data[rva2off(r):rva2off(r)+0x1A0]
n=0
for ins in md.disasm(seg, IB+r):
    print("  %08X (RVA %06X) %-10s %s" % (ins.address, ins.address-IB, ins.mnemonic, ins.op_str))
    n+=1
    if n>70: break