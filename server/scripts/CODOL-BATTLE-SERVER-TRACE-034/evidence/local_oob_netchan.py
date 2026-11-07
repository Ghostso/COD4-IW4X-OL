import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
print("=== 0x5C05F0 OOB dispatcher: real function entry? ===")
for ins in md.disasm(d[0x1C05F0:0x1C0620], 0x1C05F0):
    print("  RVA %08X  %-16s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
print()
print("=== local netchan candidates: sites containing immediate 1154 (0x482) ===")
for rva in (0x1AC178, 0x3E5960, 0x3E5A57, 0x5C2034):
    print("  --- RVA %X  (bytes %s) ---" % (rva, d[rva-8:rva+12].hex()))
    for ins in md.disasm(d[max(0,rva-0x20):rva+0x20], max(0,rva-0x20)):
        print("      RVA %08X  %-16s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
