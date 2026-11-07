from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
tgt=0x4FD287
# 正确对齐：从 tgt 往前找一个偏移，使得到 tgt 恰好是 call
best=None
for back in range(1,300):
    st=tgt-back
    o=st-base
    ins=list(md.disasm(d[o:o+back+6], st))
    hit=None
    for x in ins:
        if x.address==tgt and x.mnemonic=="call": hit=x; break
        if x.address>tgt: break
    if hit:
        # 找函数头（push ebp;mov ebp,esp 或 push -1;push imm）
        for b2 in range(0,back+1):
            off2=st-base-b2
            if off2<0: break
            if d[off2]==0x55 and d[off2+1]==0x8B and d[off2+2]==0xEC:
                best=(base+off2, back, b2); break
        if best: break
print("函数入口 = 0x%08X"%(best[0] if best else 0))
if best:
    ent=best[0]; so=ent-base
    print()
    print("==== 0x%08X 前 100 条 ===="%ent)
    c=0
    for ins in md.disasm(d[so:so+0x400], ent):
        m="  <<< call 0x808650" if ins.address==0x4FD287 else ""
        print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,m)); c+=1
        if c>=100: break
