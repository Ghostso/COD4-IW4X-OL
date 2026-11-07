# -*- coding: utf-8 -*-
"""TASK-034: delta-dispatcher caller chain + region context (local target image)."""
import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def dis(r,n,label):
    print("--- %s  RVA %X ---" % (label,r))
    for ins in md.disasm(d[r:r+n], r):
        print("   RVA %08X  %-18s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
dis(0x208380,0x40,"caller of delta dispatcher (0x208432 calls 0x5F830)")
dis(0x1FF820,0x50,"caller of 0x208380 (site 0x1FFB88)")
print()
print("== delta dispatcher signature (function RVA 0x5F830) ==")
dis(0x5F830,0x40,"delta-field type dispatcher entry")
print()
print("== the two type-index tables ==")
print("  A: index table RVA 0x460550 (len 0x13A=314), targets table RVA 0x46040C (handle count 81)")
print("  B: index table RVA 0x4606E4 (len 0x88=136),  targets table RVA 0x46068C (handle count 22)")
