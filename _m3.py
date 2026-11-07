import struct, os, capstone
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
p=os.path.join(D,"snap_002.bin"); LO=0x00010000
data=open(p,"rb").read()
def rd(va,n):
    return data[va-LO:va-LO+n]
def dis(va,n=64,label=""):
    code=rd(va,n)
    md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    print("---- %s VA=0x%08X ----"%(label,va))
    if len(code)<n: print("   (short read %d)"%len(code)); return
    for i in md.disasm(code,va):
        print("  0x%08X  %-8s %s"%(i.address,i.mnemonic,i.op_str))
dis(0x07765A0,80,"reader 0x7765A0")
print()
dis(0x0B774E0,48,"readBits 0xB774E0")
print()
dis(0x0B77B10,48,"writeBits 0xB77B10")
