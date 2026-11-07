import struct, os, capstone
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read(); LO=0x00010000
def off(va): return va-LO
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def prologue(va,back=0x300):
    for b in range(0,back):
        v=va-b
        if data[off(v):off(v)+3]==b"\x55\x8B\xEC": return v
    return va
for tgt,label,n in [(0x00B765A0,"READER 0xB765A0",0x120),
                    (0x00B9BBB0,"getBuf 0xB9BBB0",0x80),
                    (0x00BA41D0,"pre-check 0xBA41D0",0x60),
                    (0x00BA0CC0,"pre-check 0xBA0CC0",0x60)]:
    s=prologue(tgt)
    print("==== %s  (prologue 0x%08X) ===="%(label,s))
    code=data[off(s):off(s)+n]
    cnt=0
    for i in md.disasm(code,s):
        print("  0x%08X  %-9s %s"%(i.address,i.mnemonic,i.op_str))
        cnt+=1
        if cnt>=38: break
    print()
