import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
lo,hi = 0xDC7360, 0xDC7900
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True
hits=[]
# linear sweep from 0x401000 to 0xE65000
start=0x401000
code=d[start-BASE:]
for ins in md.disasm(code, start):
    for op in ins.operands:
        if op.type==capstone.x86.X86_OP_IMM:
            v=op.imm & 0xffffffff
            if lo<=v<hi: hits.append((ins.address, ins.mnemonic, ins.op_str, v))
        elif op.type==capstone.x86.X86_OP_MEM and op.mem.base==0 and op.mem.index==0:
            v=op.mem.disp & 0xffffffff
            if lo<=v<hi: hits.append((ins.address, ins.mnemonic, ins.op_str, v))
print("refs to table region [%08X,%08X): %d" % (lo,hi,len(hits)))
for a,m,o,v in hits[:60]:
    print("  %08X  %-8s %-40s  -> %08X" % (a,m,o,v))
