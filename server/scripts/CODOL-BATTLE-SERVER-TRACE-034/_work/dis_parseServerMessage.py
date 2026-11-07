import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def dis(va,n,label):
    print("="*112); print("%s   VA=%08X RVA=%08X" % (label,va,va-BASE)); print("="*112)
    for ins in md.disasm(d[va-BASE:va-BASE+n],va):
        print("%08X  %-20s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
dis(0x46E6D0, 0x150, "parseServerMessage  (probe RVA 0x6E6A0 -> VA 0x46E6A0)")
