import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def dis(rva,n,label):
    print("="*112); print("%s  VA=%08X RVA=%08X" % (label,rva+BASE,rva)); print("="*112)
    for ins in md.disasm(d[rva:rva+n], rva):
        print("VA %08X  RVA %08X  %-18s %s %s" % (ins.address+BASE, ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
dis(0x6D060, 0x60, "parseMatchState candidate (probe RVA 0x6D060)")
