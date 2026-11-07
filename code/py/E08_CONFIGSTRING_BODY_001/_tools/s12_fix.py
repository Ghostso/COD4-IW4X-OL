import sys; sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32)
IB=S.IB
print("RULE: capstone prints VA. Immediate operands in code are VA. RVA = VA - 0x%X" % IB)
print()
print("=== format strings (VA -> RVA -> bytes) ===")
for va in (0x7C0A00,0x7C0A05,0x7C0A0E,0x7C0A13,0x7C0A00+0x10):
    rva=va-IB
    b=S.bytes_rva(rva,60)
    print("  VA 0x%X -> RVA 0x%X -> %r" % (va,rva,(b.split(b'\0')[0] if b else None)))
print()
print("=== index writer continuation, RVA 0xA044E (je target) ===")
o,_=S.off(0xA044E); k=0
for ins in md.disasm(S.d[o:o+80], IB+0xA044E):
    print("  %06X %-18s %s" % (ins.address-IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=16: break
print()
print("=== MSG_WriteData tail RVA 0x994D4 ===")
o,_=S.off(0x994D4); k=0
for ins in md.disasm(S.d[o:o+80], IB+0x994D4):
    print("  %06X %-18s %s" % (ins.address-IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=16: break