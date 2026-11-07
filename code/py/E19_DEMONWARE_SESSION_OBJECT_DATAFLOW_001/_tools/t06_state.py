import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("=== state machine jump table VA 0xAAC090 (RVA 0x6AC090) ===")
o,_=C.off(0x6AC090)
for i in range(4):
    v=struct.unpack_from("<I",C.d,o+i*4)[0]
    print("   state %d -> RVA 0x%X"%(i,(v-0x400000)&0xffffffff))
print()
# 0x788133 site real function
print("=== 0x788133 site (E-16 said recv here) ===")
o2,_=C.off(0x788120)
for ins in md.disasm(C.d[o2:o2+0x40],C.IB+0x788120):
    print("  %06X %-18s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
print()
print("=== 0x78772D region recheck (E-16: timestamp) ===")
o3,_=C.off(0x78772D)
for ins in md.disasm(C.d[o3:o3+0x30],C.IB+0x78772D):
    print("  %06X %-18s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
print()
print("=== object field map of 0x6ABBC0 owner (esi) ===")
for off in (0x98,0x9c,0xa0,0xa4,0xa8,0xac,0xb0,0xb4,0xc4,0xc8,0x108):
    print("   +0x%X"%(off))
