from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# SEH 函数头特征: 6A FF 68 xx xx xx xx
o=0x4FD287-base
ent=None
for delta in range(0,0x400):
    off=o-delta
    if d[off]==0x6A and d[off+1]==0xFF and d[off+2]==0x68:
        ent=base+off; break
print("SEH 函数入口 0x%08X"%ent)
if ent:
    so=ent-base
    print()
    print("==== 0x%08X 前 80 条 ===="%ent)
    c=0
    for ins in md.disasm(d[so:so+0x300], ent):
        m="  <<< call 0x808650" if ins.address==0x4FD287 else ""
        print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,m)); c+=1
        if c>=75: break
    print()
    # 找调用该函数的点
    res=[]
    for off in range(len(d)-5):
        if d[off]==0xE8:
            rel=struct.unpack_from("<i", d, off+1)[0]
            if base+off+5+rel==ent: res.append(base+off)
    print("=== call 0x%08X 调用者 %d ==="%(ent,len(res)))
    for va in res[:10]:
        st=max(0,va-base-32)
        print("  --- 0x%08X ---"%va)
        for x in md.disasm(d[st:va-base+6], base+st):
            mm="  <<<" if va-5<x.address<=va+5 else ""
            print("      %08X  %-18s %s %s%s"%(x.address,x.bytes.hex(),x.mnemonic,x.op_str,mm))
