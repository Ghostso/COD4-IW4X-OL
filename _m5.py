import struct, os, capstone
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
p=os.path.join(D,"snap_002.bin"); LO=0x00010000
data=open(p,"rb").read()
def off(va): return va-LO
tgt=0x007765A0
# search backwards for prologue 55 8B EC
start=None
for back in range(1,0x400):
    va=tgt-back; o=off(va)
    if data[o:o+3]==b"\x55\x8B\xEC":
        start=va; break
print("nearest prologue before 0x%08X: %s"%(tgt, hex(start) if start else "none"))
print("bytes before target:", data[off(tgt)-32:off(tgt)].hex(" "))
print()
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
if start:
    code=data[off(start):off(start)+0x160]
    for i in md.disasm(code,start):
        mark = "  <== 0x7765A0" if i.address==tgt else ""
        print("  0x%08X  %-9s %-32s%s"%(i.address,i.mnemonic,i.op_str,mark))
        if i.address>tgt+0x60: break
