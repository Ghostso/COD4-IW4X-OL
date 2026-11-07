import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def dis(lo,hi,label):
    print("="*100); print("%s  RVA %X..%X (VA %X..%X)" % (label,lo,hi,lo+BASE,hi+BASE)); print("="*100)
    for ins in md.disasm(d[lo:hi],lo):
        print("RVA %08X  %-18s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
dis(0x6E480,0x6E6D0,"function containing probe RVA 0x6E6A0")
