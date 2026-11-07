from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
def callers(tgt):
    res=[]
    for off in range(len(d)-5):
        if d[off]==0xE8:
            rel=struct.unpack_from("<i", d, off+1)[0]
            if base+off+5+rel==tgt: res.append(base+off)
    return res
for tgt,name in [(0x7E98F0,"大初始化(开门1)")]:
    res=callers(tgt)
    print("=== call 0x%08X (%s) 调用者 %d ==="%(tgt,name,len(res)))
    for va in res:
        st=max(0,va-base-40)
        print("  --- 0x%08X ---"%va)
        for x in md.disasm(d[st:va-base+6], base+st):
            m="  <<<" if va-5<x.address<=va+5 else ""
            print("      %08X  %-18s %s %s%s"%(x.address,x.bytes.hex(),x.mnemonic,x.op_str,m))
        print()
