import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def dis(va,n,label):
    print("="*100); print("%s VA=%08X"%(label,va)); print("="*100)
    for ins in md.disasm(d[va-BASE:va-BASE+n],va):
        print("%08X  %-20s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
dis(0x5BF990,0x90,"near 0x5BF9D9 (refs 0xDC69C0)")
