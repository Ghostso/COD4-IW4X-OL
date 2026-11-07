from capstone import *
import struct, re
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
def s(va,n=100):
    o=va-base
    if o<0 or o>=len(d): return "<out>"
    e=d.find(b"\x00",o)
    return d[o:min(e if e>0 else o+n,o+n)].decode("latin1","replace")
print("=== 连接参数字符串 ===")
for va in (0x81A76E8,0xDBCF88,0xDBD8CC):
    print("   0x%08X %r"%(va,s(va)))
print()
# 0x77F8B3 所在函数
o=0x77F8B3-base
ent=None
for k in range(1,0x600):
    off=o-k
    if d[off]==0xCC and d[off+1]==0xCC and d[off+2]==0xCC:
        ent=base+off+1
        while d[ent-base]==0xCC: ent+=1
        break
print("0x77F8B3 所在函数入口 0x%08X"%ent)
if ent:
    so=ent-base; c=0
    print()
    print("==== 0x%08X 前 55 条 ===="%ent)
    for ins in md.disasm(d[so:so+0x260], ent):
        m="  <<< call 0x4FD9B0" if ins.address==0x77F8B3 else ""
        print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,m)); c+=1
        if c>=55: break
    res=[]
    for off2 in range(len(d)-5):
        if d[off2]==0xE8:
            rel=struct.unpack_from("<i", d, off2+1)[0]
            if base+off2+5+rel==ent: res.append(base+off2)
    print()
    print("=== call 0x%08X 调用者 %d ==="%(ent,len(res)))
    for va in res[:12]: print("   0x%08X"%va)
