import pefile, struct
from capstone import *
from capstone.x86 import *
P = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(P,"rb").read()
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S=[]
for s in pe.sections:
    S.append((s.Name.rstrip(b"\x00").decode(), s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData))
def rva2off(rva):
    for nm,v,vs,rp,rs in S:
        if v<=rva<v+min(vs,rs): return rp+(rva-v)
    return None
def va2off(va): return rva2off(va-IB)
def off2rva(off):
    for nm,v,vs,rp,rs in S:
        if rp<=off<rp+rs: return v+(off-rp)
    return None
print("=== mapping verification ===")
for rva,expect in [(0x1AC1D0,0x1AB5D0),(0xA2E50,0xA2250)]:
    print(" RVA 0x%X -> off 0x%X (expect 0x%X) %s" % (rva, rva2off(rva), expect, "OK" if rva2off(rva)==expect else "MISMATCH"))
print()
print("=== raw bytes at RVA 0xA2E40..0xA2E80 (off 0xA2240) ===")
o=rva2off(0xA2E40)
print(data[o:o+0x40].hex(" "))
print()
print("=== disasm RVA 0xA2D80..0xA2E90 ===")
md=Cs(CS_ARCH_X86, CS_MODE_32)
o=rva2off(0xA2D80); lo=IB+0xA2D80
n=0
for ins in md.disasm(data[o:o+0x120], lo):
    print("  %08X (RVA %06X)  %-10s %s" % (ins.address, ins.address-IB, ins.mnemonic, ins.op_str))
    n+=1
    if n>90: break