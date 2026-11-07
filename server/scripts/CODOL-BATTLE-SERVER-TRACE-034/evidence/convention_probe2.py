import capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def show(off, label, n=40):
    print("--- %s : file offset 0x%X ---" % (label, off))
    if off+16 > len(d): print("   OUT OF RANGE"); return
    count=0
    for ins in md.disasm(d[off:off+n*6], off):
        print("   %08X  %-16s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        count+=1
        if count>=n: break
for va,name in [(0x467520,"packetEvent VA"),(0x5A5960,"netchanProcess VA"),(0x46BF80,"decodeMessage VA"),(0x46D170,"parseSnapshot VA")]:
    show(va, name+" @ off=VA")
    show(va-BASE, name+" @ off=VA-0x400000")
    print()
