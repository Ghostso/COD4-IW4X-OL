import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for va,n,lab in [(0x62F180,0x70,"around 0x62F1B9"),(0x775880,0x50,"around 0x775895"),(0x775A40,0x50,"around 0x775A69")]:
    print("="*100); print("%s VA=%08X"%(lab,va)); print("="*100)
    for ins in md.disasm(d[va-BASE:va-BASE+n],va):
        print("%08X  %-20s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
