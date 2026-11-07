# -*- coding: utf-8 -*-
import sys,pickle,bisect,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
sec=C.pe.sections[0];o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]
base=C.IB+sec.VirtualAddress
# search for cmp reg, 4 / cmp byte/word/dword [..],4 and movzx ... then cmp eax,4 within a 32-insn window
hits=[]
window=[]
for ins in md.disasm(text,base):
    r=ins.address-C.IB
    window.append(ins)
    if len(window)>28: window.pop(0)
    if ins.mnemonic=='cmp':
        vals=[]
        for op in ins.operands:
            if op.type==X86_OP_IMM: vals.append(op.imm)
        if 4 in vals:
            # is there a preceding byte read within 12 insns?
            ctx=[w for w in window[:-1]]
            read=False; read_desc=[]
            for w in ctx[-12:]:
                if w.mnemonic in ('movzx','movsx') and ('byte ptr' in w.op_str):
                    read=True; read_desc.append('%X:%s %s'%(w.address-C.IB,w.mnemonic,w.op_str))
            hits.append((r,ins.mnemonic+' '+ins.op_str,read,read_desc))
print("cmp #4 count:",len(hits))
for r,s,read,rd in hits:
    if read:
        print("  0x%06X %-28s read_ctx=%s"%(r,s,'; '.join(rd)))
