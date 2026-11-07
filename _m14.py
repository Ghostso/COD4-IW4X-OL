import struct, os, capstone
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read(); LO=0x00010000
def off(va): return va-LO
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for site in (0x00BA1A37,0x0063702C,0x0071EE4A):
    s=site-0x50
    print("==== context around call to 0xB779A0 @0x%08X ===="%site)
    c=0
    for i in md.disasm(data[off(s):off(s)+0x80],s):
        mark="  <== init" if i.address==site else ""
        print("  0x%08X  %-9s %-30s%s"%(i.address,i.mnemonic,i.op_str,mark)); c+=1
        if c>30: break
    print()
print("==== bit reader ctor 0xB779A0 (rest) ====")
c=0
for i in md.disasm(data[off(0xB779A0):off(0xB779A0)+0xB0],0xB779A0):
    print("  0x%08X  %-9s %s"%(i.address,i.mnemonic,i.op_str)); c+=1
    if c>34: break
