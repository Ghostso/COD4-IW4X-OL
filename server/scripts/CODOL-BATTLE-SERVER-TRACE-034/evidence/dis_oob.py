import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def dis(va, n, label):
    print("="*110); print("%s   VA=%08X  RVA=%08X" % (label, va, va-BASE)); print("="*110)
    for ins in md.disasm(d[va-BASE:va-BASE+n], va):
        print("%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
dis(0x5C0600, 0x260, "OOB connectionless handler (getchallenge @5C071E, heartbeat @5C0EBB)")
