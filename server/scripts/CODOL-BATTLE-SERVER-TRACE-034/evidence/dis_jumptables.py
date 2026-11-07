import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def dis(va,n,label):
    print("="*112); print("%s  VA=%08X RVA=%08X" % (label,va,va-BASE)); print("="*112)
    for ins in md.disasm(d[va-BASE:va-BASE+n],va):
        print("%08X  %-20s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
dis(0x45F860, 0x80, "dispatcher near 0x45F89B (table A)")
dis(0x460170, 0x70, "dispatcher near 0x4601A4 (table B)")
print()
print("=== full table A @0x46040C (16 entries) ===")
for i in range(16):
    print("   [%2d] %08X" % (i, struct.unpack_from("<I",d,(0x46040C-BASE)+i*4)[0]))
print("=== full table B @0x46068C (16 entries) ===")
for i in range(16):
    print("   [%2d] %08X" % (i, struct.unpack_from("<I",d,(0x46068C-BASE)+i*4)[0]))
