# -*- coding: utf-8 -*-
"""045: close the receive->decode edge and enumerate callers of the decoders (correct VA space)."""
import sys, struct
sys.stdout.reconfigure(encoding="utf-8")
import capstone
IMG=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
b=open(IMG,"rb").read(); IB=0x400000
LO,HI=0x1000,0x8a7000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32); md.detail=True
targets={"0x87BA50 thunk":0x87BA50,"0x87BE00 recv-prim":0x87BE00,"0x87C110 dec1":0x87C110,"0x87D5A0 dec2":0x87D5A0,"0x87A890 sizeinfo-writer":0x87A890}
print("=== all direct E8 call sites into the net family (VA-space corrected) ===")
for name,rva in targets.items():
    tva=IB+rva; hits=[]
    for i in range(LO,HI-5):
        if b[i]==0xE8:
            rel=struct.unpack("<i",b[i+1:i+5])[0]
            if IB+i+5+rel==tva: hits.append(i)
    print("  %-24s RVA %08X : %d callers %s"%(name,rva,len(hits),["RVA %08X"%h for h in hits]))
print()
print("=== call sequence inside function containing 0x85D96E (calls thunk then dec2) ===")
for i in (0x85D96E,0x85D9B5,0x85D9F7,0x85D49D,0x85E71A,0x85E74E):
    lo=i-16
    print("  --- around RVA %08X ---"%i)
    for ins in md.disasm(b[lo:lo+40], IB+lo):
        print("     %08X %-16s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
