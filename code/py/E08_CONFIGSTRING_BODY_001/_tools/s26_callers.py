import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=S.off(0x1000); text=S.d[o:o+S.pe.sections[0].SizeOfRawData]
TARGET=0x1A07B0  # the self-contained 1-bit reader function
print("=== callers of client 1-bit reader RVA 0x1A07B0 (VA 0x%X) ===" % (S.IB+TARGET))
calls=[]
for ins in sweep(md, text, S.IB+0x1000):
    if ins.id in (X86_INS_CALL,X86_INS_JMP):
        for op in ins.operands:
            if op.type==X86_OP_IMM and op.imm-S.IB==TARGET:
                calls.append(ins.address-S.IB)
print("direct callers:",len(calls))
for a in calls[:40]: print("   call site RVA 0x%X" % a)
print()
# also check the family: functions whose body starts at 0x1A07xx
print("=== nearby function starts (prologue scan 0x1A0600..0x1A0900) ===")
o,_=S.off(0x1A0600)
k=0
for ins in md.disasm(S.d[o:o+0x300], S.IB+0x1A0600):
    if ins.mnemonic=="push" and ins.op_str=="ebp": print("   prologue @ RVA 0x%X" % (ins.address-S.IB))
    k+=1
print()
print("=== inspect one caller context (first 3) ===")
for a in calls[:3]:
    s=max(0,a-0x60)
    print("--- around call site 0x%X ---" % a)
    oo,_=S.off(s); k=0
    for ins in md.disasm(S.d[oo:oo+0x90], S.IB+s):
        mark=" <== CALL" if ins.address-S.IB==a else ""
        print("   %06X %-16s %s%s" % (ins.address-S.IB, bytes(ins.bytes).hex(), ins.mnemonic+" "+ins.op_str, mark)); k+=1
        if k>=22: break
    print()