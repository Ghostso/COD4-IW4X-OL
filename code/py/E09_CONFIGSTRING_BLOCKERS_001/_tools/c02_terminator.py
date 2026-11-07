import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== client 0xA2660 AFTER the A3 loop: RVA 0xA291C .. 0xA29C0 ===")
o,_=C.off(0xA291C); k=0
for ins in md.disasm(C.d[o:o+0xC0], C.IB+0xA291C):
    print("   %06X %-18s %s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=52: break
print()
print("=== server: does WriteData touch the bit counter? MSG_WriteData full (0x9949B) ===")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
o,_=S.off(0x9949B); k=0
for ins in md.disasm(S.d[o:o+0x64], S.IB+0x9949B):
    print("   %06X %-18s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
print()
print("=== server: WriteBits head (does it sync with [+4]?) 0x99590 ===")
o,_=S.off(0x99590); k=0
for ins in md.disasm(S.d[o:o+0x40], S.IB+0x99590):
    print("   %06X %-18s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=18: break
print()
print("=== server: core byte writer 0x994FC (what does it use?) ===")
o,_=S.off(0x994FC); k=0
for ins in md.disasm(S.d[o:o+0x60], S.IB+0x994FC):
    print("   %06X %-18s %s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str)); k+=1
    if k>=22: break