import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== the EXE_CONFIGSTRINGMISMATCH reference sites in FULL (find who pushes it) ===")
import struct
pat=struct.pack("<I",0xCB835C)
locs=[]; o=0
while True:
    i=C.d.find(pat,o)
    if i<0: break
    # which RVA?
    for s in C.secs:
        if s[3]<=i<s[3]+s[4]: locs.append(('RVA',s[1]+(i-s[3]), 'off',i))
    o=i+1
for x in locs: print("   ",x)
print()
# disasm around the code references
for _,rva,_,_ in locs:
    print("=== ref at RVA 0x%X ===" % rva)
    st=max(0,rva-0x60)
    oo,_=C.off(st); k=0
    for ins in md.disasm(C.d[oo:oo+0xA0], C.IB+st):
        m=" <== REF" if ins.address-C.IB==rva else ""
        print("   %06X %-16s %s%s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str,m)); k+=1
        if k>=26: break
    print()