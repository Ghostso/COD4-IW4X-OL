import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def dis(va, n, label):
    print("="*100); print("%s  VA=%08X" % (label, va)); print("="*100)
    for ins in md.disasm(d[va-BASE:va-BASE+n], va):
        print("%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
dis(0x6326E0, 0x0e0, "parser tail 0x6326E0..0x6327C0")
dis(0x632860, 0x0b0, "parser exits 0x632860..0x632910")
