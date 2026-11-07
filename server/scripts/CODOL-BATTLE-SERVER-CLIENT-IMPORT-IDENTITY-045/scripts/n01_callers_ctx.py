# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
import capstone
IMG=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
b=open(IMG,"rb").read(); IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
def dis(lo,hi,title):
    print("="*30, title)
    for ins in md.disasm(b[lo:hi], IB+lo):
        mark=" <<< call thunk 87BA50" if ins.address==IB+0x85D96E or ins.address==IB+0x85E71A else ""
        print("  %08X  %-20s %s %s%s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
dis(0x85D8D0,0x85DA40,"caller #1 @RVA 0x85D96E")
dis(0x85E6A0,0x85E7C0,"caller #2 @RVA 0x85E71A (+handler)")
