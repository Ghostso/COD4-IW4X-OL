# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
sec=C.pe.sections[0];o,_=C.off(sec.VirtualAddress);text=C.d[o:o+sec.SizeOfRawData];base=C.IB+sec.VirtualAddress
# linear scan, track last 12 instructions
hist=[]; hits=[]
for ins in md.disasm(text,base):
    hist.append(ins)
    if len(hist)>16: hist.pop(0)
    if ins.mnemonic=='call':
        for op in ins.operands:
            if op.type==X86_OP_IMM:
                tgt=(op.imm-C.IB)&0xffffffff
                if tgt in (0x1AC670,0x1AC1D0,0x1AC7B0,0x1AC7E0,0x1AC800,0x1AC850,0x1AC8A0,0x1ACAA0):
                    # find nearest preceding push imm
                    pushes=[]
                    for x in reversed(hist[:-1]):
                        if x.mnemonic=='push':
                            for oo in x.operands:
                                if oo.type==X86_OP_IMM: pushes.append(oo.imm)
                            break
                        if x.mnemonic in ('call','ret','jmp'): break
                    hits.append((ins.address-C.IB,tgt,pushes[0] if pushes else None))
print("total read-primitive calls:",len(hits))
from collections import Counter
print("by target:",Counter(hex(t) for _,t,_ in hits))
print()
# print hits whose preceding push is 1 or 8, grouped by function-ish rva (nearest preceding push ebp;mov ebp,esp or push ecx;mov ebp,esp)
def region(r):
    return (0x340000<=r<0x360000) or (0xA2000<=r<0xA3000) or (0x60000<=r<0x70000) or (0x1AC000<=r<0x1B0000)
for site,tgt,pushv in hits:
    if pushv in (1,8) and region(site):
        # find nearest preceding function-ish prologue within 2000 bytes
        print("  site 0x%06X -> 0x%06X push=%s"%(site,tgt,pushv))
