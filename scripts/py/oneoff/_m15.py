import struct, os, capstone
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read(); LO=0x00010000
def off(va): return va-LO
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def more(va,start=None,n=0x90,label=""):
    s=start or va
    print("==== %s @0x%08X ===="%(label,va))
    c=0
    for i in md.disasm(data[off(s):off(s)+n],s):
        print("  0x%08X  %-9s %s"%(i.address,i.mnemonic,i.op_str)); c+=1
        if c>34: break
    print()
more(0xB779A0,0xB779F9,0x70,"ctor tail")
more(0xBA1A37,0xBA1A3E,0x90,"0xBA1A3E ctx (what is [esi+4..]?)")
# also: enumerate all call targets from 0xBA4430 function body to see what it dispatches to
