from capstone import *
import struct, re
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 找 0x4FDA03 所在函数入口
o=0x4FDA03-base
ent=None
for k in range(1,0x600):
    off=o-k
    if d[off]==0xCC and d[off+1]==0xCC and d[off+2]==0xCC:
        ent=base+off+1
        while d[ent-base]==0xCC: ent+=1
        break
print("0x4FDA03 所在函数入口 0x%08X"%ent)
so=ent-base
print()
print("==== 0x%08X 前 60 条 ===="%ent)
c=0
for ins in md.disasm(d[so:so+0x280], ent):
    m="  <<< call 0x4FCEE0" if ins.address==0x4FDA03 else ""
    print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,m)); c+=1
    if c>=58: break
print()
res=[]
for off2 in range(len(d)-5):
    if d[off2]==0xE8:
        rel=struct.unpack_from("<i", d, off2+1)[0]
        if base+off2+5+rel==ent: res.append(base+off2)
print("=== call 0x%08X 调用者 %d ==="%(ent,len(res)))
for va in res[:12]: print("   0x%08X"%va)
