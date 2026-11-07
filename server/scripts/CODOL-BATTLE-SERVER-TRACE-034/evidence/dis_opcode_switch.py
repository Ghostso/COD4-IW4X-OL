# -*- coding: utf-8 -*-
"""TASK-034: examine the two 6-way opcode switches adjacent to the delta-dispatcher caller chain."""
import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def entry_back(r, back=0x2000):
    for p in range(r,r-back,-1):
        if p<=0: break
        if d[p-1]==0xCC and (d[p:p+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[p:p+2]==b"\x8b\xff"):
            return p
    return None
for site in (0x1FB64,0x1FBFB):
    print("site RVA %X -> enclosing entry RVA %X" % (site, entry_back(site)))
print()
print("== region 0x1FB00..0x1FC20 ==")
for ins in md.disasm(d[0x1FB00:0x1FC20], 0x1FB00):
    print("  RVA %08X  %-20s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
