import pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
def off(r):
    for s in pe.sections:
        if s.VirtualAddress<=r<s.VirtualAddress+s.Misc_VirtualSize:
            return s.PointerToRawData+r-s.VirtualAddress if s.SizeOfRawData and r-s.VirtualAddress<s.SizeOfRawData else None
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o=off(0x6B95C0)
print("== 0x6B95C0 ==")
if o: 
    for ins in md.disasm(d[o:o+0x60],IB+0x6B95C0):
        print("%06X %-18s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
else: print("NO_RAW")
# also confirm 0xA87830 tail
o=off(0x687883)
print("== 0xA87830 tail ==")
for ins in md.disasm(d[o:o+0x24],IB+0x687883):
    print("%06X %-18s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
