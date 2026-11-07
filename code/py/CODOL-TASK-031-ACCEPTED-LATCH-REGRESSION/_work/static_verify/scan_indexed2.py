import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True; md.skipdata=True
n=0; hits=[]
for ins in md.disasm(d[0x401000-BASE:0xE65000-BASE], 0x401000):
    n+=1
    try:
        ops=ins.operands
    except capstone.CsError:
        continue
    for op in ops:
        try:
            if op.type==capstone.x86.X86_OP_MEM:
                disp=op.mem.disp & 0xffffffff
                if 0xDC6000<=disp<0xDC9000: hits.append((ins.address,ins.mnemonic,ins.op_str,disp))
            elif op.type==capstone.x86.X86_OP_IMM:
                v=op.imm & 0xffffffff
                if 0xDC6000<=v<0xDC9000: hits.append((ins.address,ins.mnemonic,ins.op_str,v))
        except capstone.CsError:
            continue
print("decoded %d instructions; hits=%d" % (n,len(hits)))
for h in hits[:80]:
    print("  %08X  %-7s %-46s -> %08X" % h)
