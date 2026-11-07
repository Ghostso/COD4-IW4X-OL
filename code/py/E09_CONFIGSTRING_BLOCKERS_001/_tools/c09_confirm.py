import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=None
from capstone import *
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== SERVER growth block RAW BYTES (0x9960A..0x99637) ===")
o,_=S.off(0x9960A)
print("   ", S.d[o:o+0x2E].hex(" "))
print("=== decode 0x9960A..0x99636 to confirm resync ===")
k=0
for ins in md.disasm(S.d[o:o+0x2C], S.IB+0x9960A):
    print("   %06X %-20s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
print()
print("=== does 0x99651 (WriteLenStr) modify bitpos? whole body bytes ===")
o2,_=S.off(0x99651)
print("   ", S.d[o2:o2+0x3E].hex(" "))
print()
print("=== SANITY: is there any 'mov [r+0x10]' inside 0x99651? ===")
found=False
for ins in md.disasm(S.d[o2:o2+0x3E], S.IB+0x99651):
    if "0x10]" in ins.op_str and ins.mnemonic in ("mov","add","sub","or","and"): found=True; print("   ",ins.mnemonic,ins.op_str)
print("   result:",found)