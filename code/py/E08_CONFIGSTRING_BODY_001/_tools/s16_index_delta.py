import sys; sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== index-delta writer RVA 0xA0400..0xA0468 (NOTE: RVAs, not VAs) ===")
o,_=S.off(0xA0400); k=0
for ins in md.disasm(S.d[o:o+0x70], S.IB+0xA0400):
    print("  %06X %-20s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
print()
print("=== confirm 0x499551/2/4 semantics: are they WriteByte/Short/Long? ===")
for rva,cnt,lab in ((0x99551,1,"one byte"),(0x99566,2,"two bytes"),(0x9957B,4,"four bytes")):
    o,_=S.off(rva)
    print("  RVA 0x%X (%s):" % (rva,lab))
    k=0
    for ins in md.disasm(S.d[o:o+20], S.IB+rva):
        print("     %06X %s" % (ins.address-S.IB, ins.mnemonic+" "+ins.op_str)); k+=1
        if k>=5: break