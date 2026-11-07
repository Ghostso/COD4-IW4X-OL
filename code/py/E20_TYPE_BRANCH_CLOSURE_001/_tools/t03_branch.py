import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_tools")
from pe_helper import PE
from capstone import *
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(p)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("=== precise branch bytes 0x6A9969..0x6A9982 ===")
o,_=C.off(0x6A9969)
print("  raw:",C.d[o:o+0x1A].hex(" "))
for ins in md.disasm(C.d[o:o+0x1A],C.IB+0x6A9969):
    print("  %06X %-20s %s"%(ins.address-0x400000,ins.mnemonic,ins.op_str))
print()
print("=== type-1 vs type-2 semantic note ===")
print("  al = type code (from [esi+0xa8])")
print("  bl = 1")
print("  cmp al,bl ; je 0x6A9978   -> type==1 jumps, ebx already 1, then FALLS INTO 0x6A9978 which sets ebx=9")
print("  cmp al,2  ; jne 0x6A997D  -> type==2 also reaches 0x6A9978 (ebx=9)")
print("  => BOTH type 1 and type 2 end with ebx=9")
print()
print("=== so where does ebx differ? check 0x6A9978 vs 0x6A997D ===")
o2,_=C.off(0x6A9978)
for ins in md.disasm(C.d[o2:o2+0x10],C.IB+0x6A9978):
    print("  %06X %-16s %s"%(ins.address-0x400000,ins.mnemonic,ins.op_str))
print()
print("=== payload copy at 0x6A9A30 (second memcpy) length ===")
o3,_=C.off(0x6A9A0F)
for ins in md.disasm(C.d[o3:o3+0x40],C.IB+0x6A9A0F):
    print("  %06X %-16s %s"%(ins.address-0x400000,ins.mnemonic,ins.op_str))
