import struct, os, capstone
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read(); LO=0x00010000
def off(va): return va-LO
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
print("==== full 0xBA41D0 (state reset / buffer setup) ====")
code=data[off(0xBA41D0):off(0xBA41D0)+0x260]
for i in md.disasm(code,0xBA41D0):
    print("  0x%08X  %-9s %s"%(i.address,i.mnemonic,i.op_str))
    if i.address>0xBA43F0: break
