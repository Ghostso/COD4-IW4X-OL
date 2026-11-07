import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# TRUE boundary of 0x6ABBC0
o,_=C.off(0x6ABBC0)
last=None
print("=== true body of 0x6ABBC0 (first ret) ===")
for ins in md.disasm(C.d[o:o+0x100],C.IB+0x6ABBC0):
    print("  %06X %-18s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
    if ins.mnemonic=="ret": break
print()
# all immediate call targets inside 0x6ABBC0..0x6ABC7E
print("=== real callees ===")
for ins in md.disasm(C.d[o:o+0xBE],C.IB+0x6ABBC0):
    if ins.mnemonic=="call":
        for op in ins.operands:
            if op.type==X86_OP_IMM:
                print("   0x%06X -> RVA 0x%X"%(ins.address-C.IB,(op.imm-C.IB)&0xffffffff))
print()
# who references VA 0x00AABBC0 as immediate?
tv=0x400000+0x6ABBC0
sec=C.pe.sections[0]; o2,_=C.off(sec.VirtualAddress)
text=C.d[o2:o2+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
print("=== immediate refs / dataptr to 0x6ABBC0 ===")
for ins in sweep(md,text,base):
    for op in ins.operands:
        if op.type==X86_OP_IMM and (op.imm&0xffffffff)==tv:
            print("   imm 0x%06X"%(ins.address-C.IB))
for s in C.pe.sections:
    if s.SizeOfRawData==0: continue
    oo,_=C.off(s.VirtualAddress); raw=C.d[oo:oo+s.SizeOfRawData]
    for i in range(0,max(0,len(raw)-3)):
        if struct.unpack_from("<I",raw,i)[0]==tv:
            print("   dataptr %s 0x%X"%(s.Name.rstrip(b'\0').decode(errors='replace'),s.VirtualAddress+i))
