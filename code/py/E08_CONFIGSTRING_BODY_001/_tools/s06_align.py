import pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
d=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S=[(s.Name.rstrip(b"\0").decode(),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
print("sections:", [(n,hex(v),hex(vs),hex(rp),hex(rs)) for n,v,vs,rp,rs in S])
def off(rva, want=None):
    for n,v,vs,rp,rs in S:
        if want and n!=want: continue
        if v<=rva<v+min(vs,rs): return rp+(rva-v), n
    return None,None
for r in (0x499551,0x499566,0x499590,0x499651,0x4A0400,0xA0807,0xA0997):
    o,n=off(r); print("RVA 0x%-7X -> file 0x%-8X section %s" % (r,o,n))
print()
print("=== bytes at 0x499551 .. 0x4996A0 (raw) ===")
o,_=off(0x499500)
print(d[o:o+0x1C0].hex(" "))
print()
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== proper disasm at 0x499551 ===")
o,_=off(0x499551)
n=0
for ins in md.disasm(d[o:o+96], IB+0x499551):
    print("  %08X %-18s %s" % (ins.address,bytes(ins.bytes).hex(),ins.mnemonic+" "+ins.op_str)); n+=1
    if n>=14: break