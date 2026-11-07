from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 0x4FD287 上下文
o=0x4FD287-base
for delta in range(0,0x200):
    off=o-delta
    if d[off]==0x55 and d[off+1]==0x8B and d[off+2]==0xEC:
        print("所在函数入口 0x%08X (delta=0x%X)"%(base+off,delta)); ent=base+off; break
else:
    ent=None; print("未找到入口")
if ent:
    so=ent-base
    print()
    print("==== %0x08X 起 前 70 条（含 0x4FD287）===="%ent)
    c=0
    for ins in md.disasm(d[so:so+0x300], ent):
        m="  <<< call 0x808650" if ins.address==0x4FD287 else ""
        print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,m)); c+=1
        if c>=68: break
