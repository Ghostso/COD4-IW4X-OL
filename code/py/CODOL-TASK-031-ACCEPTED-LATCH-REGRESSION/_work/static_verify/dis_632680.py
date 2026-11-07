import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail=True
def dis(va, n, label):
    print("="*100); print("%s  VA=%08X" % (label, va)); print("="*100)
    code=d[va-BASE:va-BASE+n]
    for ins in md.disasm(code, va):
        print("%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
dis(0x632680, 0x1f0, "accepted parser 0x632680")
