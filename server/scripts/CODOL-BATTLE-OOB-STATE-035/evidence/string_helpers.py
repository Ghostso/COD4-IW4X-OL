# -*- coding: utf-8 -*-
"""TASK-035: identify the string-compare helper at 0x3745E0 and confirm semantics."""
import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
print("== helper 0x3745E0 ==")
for ins in md.disasm(d[0x3745E0:0x374640],0x3745E0):
    print("  RVA %08X  %-20s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
print()
print("== neighbours 0x374900 (sprintf-like) and 0x374980 ==")
for base,lab in [(0x374900,"0x374900"),(0x374980,"0x374980")]:
    print("--- %s ---" % lab)
    n=0
    for ins in md.disasm(d[base:base+0x50],base):
        print("  RVA %08X  %-20s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
        n+=1
        if n>=14: break
