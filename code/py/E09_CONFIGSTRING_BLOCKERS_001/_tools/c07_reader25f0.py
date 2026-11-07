import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== CLIENT 0xA25F0 (per-record string/entry reader, called at 0xA2751) ===")
o,_=C.off(0xA25F0); k=0
for ins in md.disasm(C.d[o:o+0x90], C.IB+0xA25F0):
    print("   %06X %-18s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
print()
print("=== SERVER A1 write loop 0xA0823..0xA0848 (recheck: is there a length WriteBits?) ===")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
o,_=S.off(0xA0820); k=0
for ins in md.disasm(S.d[o:o+0x30], S.IB+0xA0820):
    print("   %06X %-18s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
print()
print("=== SERVER: first pass that computes lengths, 0xA05C0..0xA0620 ===")
o,_=S.off(0xA05C0); k=0
for ins in md.disasm(S.d[o:o+0x60], S.IB+0xA05C0):
    print("   %06X %-18s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1