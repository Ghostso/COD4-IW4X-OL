import struct, os, capstone
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read(); LO=0x00010000
def off(va): return va-LO
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def show(va,n,label):
    s=va
    for b in range(0,0x200):
        v=va-b
        if data[off(v):off(v)+3]==b"\x55\x8B\xEC": s=v; break
    print("==== %s @0x%08X (prologue 0x%08X) ===="%(label,va,s))
    c=0
    for i in md.disasm(data[off(s):off(s)+n],s):
        print("  0x%08X  %-9s %s"%(i.address,i.mnemonic,i.op_str)); c+=1
        if c>30: break
    print()
show(0x00B779A0,0x90,"bitstream init 0xB779A0")
show(0x00BA0CC0,0x60,"pre 0xBA0CC0")
# who writes bitreader +0x20 / +0x1c ? scan .text for stores
BASE=0x400000; END=BASE+0x0E659000
txt=data[BASE-LO:END-LO]
import re
print("==== candidate stores to [reg+0x20] adjacent to [reg+0x1c] ====")
for m in re.finditer(rb"\x89[\x40-\x7f]\x20", txt):
    a=BASE+m.start()
    win=txt[m.start()-24:m.start()+24]
    if b"\x1c" in win:
        print("  0x%08X  %s"%(a, txt[m.start()-8:m.start()+8].hex(" ")))
