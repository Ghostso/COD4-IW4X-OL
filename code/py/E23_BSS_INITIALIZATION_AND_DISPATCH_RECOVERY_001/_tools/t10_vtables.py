import sys, struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
def rd(va,n):
    r=va-IB
    for s in pe.sections:
        if s.VirtualAddress<=r<s.VirtualAddress+s.Misc_VirtualSize:
            o=s.PointerToRawData+r-s.VirtualAddress
            if s.SizeOfRawData and r-s.VirtualAddress<s.SizeOfRawData:
                return d[o:o+n]
    return None
def sec(va):
    r=va-IB
    for s in pe.sections:
        if s.VirtualAddress<=r<s.VirtualAddress+s.Misc_VirtualSize:
            return (s.Name.rstrip(b"\0").decode(), s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData)
for v in (0xc5a31c,0xc5b0a4,0xc5beb0,0xcb324c):
    print("="*66); print("vtable/data VA %08X sec=%s"%(v,sec(v)[0] if sec(v) else None))
    b=rd(v,0x40)
    if b is None: print("  NO_RAW"); continue
    for i in range(0,0x40,4):
        val=struct.unpack_from('<I',b,i)[0]
        print("  +%02X = %08X"%(i,val))
