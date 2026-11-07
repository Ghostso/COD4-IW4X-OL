import struct, os, capstone
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read(); LO=0x00010000
def off(va): return va-LO
tgt=0x00BA44F6
start=None
for back in range(1,0x600):
    va=tgt-back
    if data[off(va):off(va)+3] in (b"\x55\x8B\xEC",):
        start=va; break
print("function prologue before 0x%08X -> %s"%(tgt, hex(start) if start else "none"))
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True
if start:
    code=data[off(start):off(start)+0x400]
    for i in md.disasm(code,start):
        mark=""
        if 0xBA44F6<=i.address<=0xBA44F6+0x120: mark="  *"
        print("  0x%08X  %-9s %-34s%s"%(i.address,i.mnemonic,i.op_str,mark))
        if i.address>0xBA44F6+0x130: break
