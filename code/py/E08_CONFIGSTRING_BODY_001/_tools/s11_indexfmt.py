import sys; sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== index writer tail: 0x4A0444 .. 0x4A0470 (continue path) ===")
o,_=S.off(0x4A0444); k=0
for ins in md.disasm(S.d[o:o+64], S.IB+0x4A0444):
    print("  %06X %-20s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=14: break
print()
print("=== format strings referenced by the writer ===")
for rva in (0x7C0A00,0x7C0A05,0x7C0A0E,0x7C0A13):
    b=S.bytes_rva(rva,48)
    print("  RVA 0x%X : %r" % (rva, b.split(b'\0')[0] if b else None))
print()
print("=== MSG_WriteData (0x9949B) and strlen-ish (0x765740) ===")
for rva,lab,n in ((0x9949B,"MSG_WriteData",22),(0x765740,"strlen?",14)):
    print("--- %s RVA 0x%X ---" % (lab,rva))
    o,_=S.off(rva); k=0
    for ins in md.disasm(S.d[o:o+90], S.IB+rva):
        print("   %06X %-16s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=n: break
    print()