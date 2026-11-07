import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True; md.skipdata=True
want={0xDC73A0,0xDC7840,0xDC73B0,0xDC7850}
hits=[]
for ins in md.disasm(d[0x401000-BASE:0xE65000-BASE],0x401000):
    try: ops=ins.operands
    except capstone.CsError: continue
    for op in ops:
        try:
            if op.type==capstone.x86.X86_OP_MEM:
                v=op.mem.disp & 0xffffffff
            elif op.type==capstone.x86.X86_OP_IMM:
                v=op.imm & 0xffffffff
            else: continue
        except capstone.CsError: continue
        if v in want: hits.append((ins.address,ins.mnemonic,ins.op_str,v))
print("hits for the two vtables:",len(hits))
for h in hits:
    print("  %08X  %-7s %-46s -> %08X" % h)
