# -*- coding: utf-8 -*-
"""TASK-035: which string literals are pushed inside each state branch of the OOB sender?"""
import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def cstr(va):
    if not (0x900000<=va<0xE40000): return None
    o=va-BASE
    if not (0<=o<len(d)): return None
    e=d.find(b'\x00',o)
    if e<0 or e-o>80: return None
    s=d[o:e]
    return s.decode('latin1') if s and all(32<=c<127 for c in s) else None
branches=[("state 3 (idx0)",0x1C070E,0x1C0776),
          ("state 4 (idx1)",0x1C0776,0x1C0E07),
          ("state 5 (idx2)",0x1C0E07,0x1C0EBB),
          ("state 6 (idx3)",0x1C0EBB,0x1C0F1B)]
for lab,lo,hi in branches:
    print("=== %s : RVA %X..%X ===" % (lab,lo,hi))
    n=0; lits=[]
    for ins in md.disasm(d[lo:hi],lo):
        n+=1
        if ins.mnemonic=="push" and ins.op_str.startswith("0x"):
            c=cstr(int(ins.op_str,16))
            if c and not c.startswith("%"): lits.append((ins.address,c))
        if ins.mnemonic=="mov" and ins.op_str.startswith("edx, 0x"):
            c=cstr(int(ins.op_str.split(", ")[1],16))
            if c: lits.append((ins.address,c))
        if n>1400: break
    for a,c in lits: print("   literal @RVA %06X : %r" % (a,c))
    if not lits: print("   (no recognised literals)")
    print()
