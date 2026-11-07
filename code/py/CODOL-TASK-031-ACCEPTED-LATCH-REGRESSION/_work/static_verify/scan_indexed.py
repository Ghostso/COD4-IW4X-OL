import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True
lo,hi=0xDC6000,0xDC9000
hits=[]
for ins in md.disasm(d[0x401000-BASE:], 0x401000):
    for op in ins.operands:
        if op.type==capstone.x86.X86_OP_MEM:
            disp=op.mem.disp & 0xffffffff
            if lo<=disp<hi:
                hits.append((ins.address, ins.mnemonic, ins.op_str, disp,
                             op.mem.base, op.mem.index, op.mem.scale))
print("mem-operand refs into [%08X,%08X): %d" % (lo,hi,len(hits)))
for h in hits[:80]:
    print("  %08X  %-7s %-42s disp=%08X base=%s index=%s scale=%d" % h)
