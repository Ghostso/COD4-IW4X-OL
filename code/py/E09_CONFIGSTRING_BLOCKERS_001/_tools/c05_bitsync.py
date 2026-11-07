import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== SERVER 0x99651 FULL (A1 string writer): does it advance [msg+0x10] (bitpos)? ===")
o,_=S.off(0x99651); k=0
for ins in md.disasm(S.d[o:o+0x70], S.IB+0x99651):
    print("   %06X %-20s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
print()
print("=== SERVER 0x99590 (WriteBits) growth/sync block, 0x9960A..0x9964C ===")
o,_=S.off(0x9960A); k=0
for ins in md.disasm(S.d[o:o+0x46], S.IB+0x9960A):
    print("   %06X %-20s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
print()
print("=== SERVER msg struct field usage summary (from these functions) ===")
print("  [msg+0x00] = buffer ptr")
print("  [msg+0x04] = BYTE count (used by WriteData as dest offset)")
print("  [msg+0x08] = capacity")
print("  [msg+0x10] = BIT position (used by WriteBits)")
print("  [msg+0x14] = overflow flag")