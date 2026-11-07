import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def imm_xrefs(t):
    res=[]; tb=struct.pack("<I",t&0xffffffff); s=0
    while True:
        i=d.find(tb,s)
        if i<0: break
        res.append(i+BASE); s=i+1
    return res
for t,name in [(0xDC73A0,"vtable_A 0xDC73A0"),(0xDC7840,"vtable_B 0xDC7840")]:
    x=imm_xrefs(t)
    print("%-20s imm32 refs (%d): %s" % (name,len(x), ", ".join("%08X"%a for a in x[:30])))
print()
# disasm around first refs
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for va in imm_xrefs(0xDC73A0)[:4] + imm_xrefs(0xDC7840)[:4]:
    print("=== around %08X ===" % va)
    for ins in md.disasm(d[va-32:va+16], va-32):
        print("  %08X  %-18s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
