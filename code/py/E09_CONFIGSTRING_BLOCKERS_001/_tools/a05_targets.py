import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== clients of 0x633FE0 / 0x6340E0 (the 0x1A07B0 dispatch targets) ===")
print("   if these lead to .def/script loading, 0x1A07B0 is a SCRIPT accessor, not netcode")
for rva in (0x633FE0,0x6340E0,0x1A0660):
    o,_=C.off(rva)
    k=0
    print("--- RVA 0x%X ---" % rva)
    for ins in md.disasm(C.d[o:o+96], C.IB+rva):
        print("   %06X %-16s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=14: break
print()
print("=== strings near 0xCB6CB8 group (script .def context) ===")
for va in range(0xCB6C80,0xCB6D40,8):
    b=C.bytes_rva(va-C.IB,64)
    if b and b[0]!=0 and 32<=b[0]<127:
        s=b.split(b'\0')[0]
        if len(s)>=4: print("   VA 0x%X : %r" % (va,s[:60]))