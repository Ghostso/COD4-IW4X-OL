import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True; md.skipdata=True
hits=[]
for ins in md.disasm(d[0x401000-BASE:0xE65000-BASE],0x401000):
    try: ops=ins.operands
    except capstone.CsError: continue
    for op in ops:
        try:
            if op.type==capstone.x86.X86_OP_MEM and (op.mem.disp & 0xffffffff)==0x288:
                hits.append((ins.address,ins.mnemonic,ins.op_str,ins.bytes.hex()))
        except capstone.CsError: continue
print("instructions referencing displacement 0x288: %d" % len(hits))
for h in hits:
    print("  %08X  %-8s %-34s  %s" % h)
