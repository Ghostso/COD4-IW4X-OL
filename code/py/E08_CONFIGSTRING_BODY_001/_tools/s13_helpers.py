import sys; sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32)
IB=S.IB
print("=== helper VA 0x765740 -> RVA 0x%X ===" % (0x765740-IB))
o,_=S.off(0x365740); k=0
for ins in md.disasm(S.d[o:o+120], IB+0x365740):
    print("  %06X %-18s %s" % (ins.address-IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=26: break
print()
print("=== 0x757270 (snprintf-like) RVA 0x%X ===" % (0x757270-IB))
o,_=S.off(0x357270); k=0
for ins in md.disasm(S.d[o:o+80], IB+0x757270):
    print("  %06X %-18s %s" % (ins.address-IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=14: break