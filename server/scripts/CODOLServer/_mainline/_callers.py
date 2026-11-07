from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
def callers(tgt, name):
    res=[]
    for off in range(len(d)-5):
        if d[off]==0xE8:
            rel=struct.unpack_from("<i", d, off+1)[0]
            if base+off+5+rel==tgt: res.append(base+off)
    print("=== call %s (0x%08X) 调用者 %d 个 ==="%(name,tgt,len(res)))
    for va in res:
        st=max(0,va-base-24)
        print("  --- 0x%08X ---"%va)
        for ins in md.disasm(d[st:va-base+8], base+st):
            m="  <<<" if va-4<ins.address<=va+4 else ""
            print("      %08X  %-18s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,m))
    return res
callers(0x7F26C0, "状态机")
print()
callers(0x7F25B0, "派生状态(0x7F25B0)")
