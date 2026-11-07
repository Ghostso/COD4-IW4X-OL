# -*- coding: utf-8 -*-
"""TASK-035: comprehensive literal scan inside each state branch (all imm-load forms)."""
import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True
def cstr(va):
    if not (0x900000<=va<0xE40000): return None
    o=va-BASE
    if not (0<=o<len(d)): return None
    e=d.find(b'\x00',o)
    if e<0 or e-o>80: return None
    s=d[o:e]
    return s.decode('latin1') if s and all(32<=c<127 for c in s) else None
branches=[("state 3",0x1C070E,0x1C0776),("state 4",0x1C0776,0x1C0E07),
          ("state 5",0x1C0E07,0x1C0EBB),("state 6",0x1C0EBB,0x1C0F1B)]
for lab,lo,hi in branches:
    lits=[]
    for ins in md.disasm(d[lo:hi],lo):
        for op in ins.operands:
            if op.type==capstone.x86.X86_OP_IMM:
                c=cstr(op.imm & 0xffffffff)
                if c: lits.append((ins.address,ins.mnemonic,ins.op_str,c))
    print("=== %s : %d literal loads ===" % (lab,len(lits)))
    seen=set()
    for a,m,o,c in lits:
        if c in seen and m!="push": continue
        seen.add(c)
        print("   @%06X %-5s %-26s %r" % (a,m,o,c))
    print()
