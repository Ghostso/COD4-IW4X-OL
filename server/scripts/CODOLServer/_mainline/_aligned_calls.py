from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 遍历真实指令边界找 call 0x7E98F0 / 0x808650
def find_calls(tgt, limit=20):
    res=[]
    # 线性扫描：从几处已知代码起点开始不易，改用"滑窗反汇编"逐条
    # 简化：对每个 E8 候选，尝试从候选前 64 字节内多个偏移开始反汇编，
    # 若能在候选处恰好得到 call tgt 指令，则接受
    for off in range(len(d)-5):
        if d[off]!=0xE8: continue
        rel=struct.unpack_from("<i", d, off+1)[0]
        if base+off+5+rel!=tgt: continue
        # 验证：从 off 往前找一个能对齐的出点
        ok=False
        for back in range(1,80):
            st=off-back
            if st<0: break
            nxt=None
            for ins in md.disasm(d[st:off+5], base+st):
                if ins.address<=base+off<ins.address+ins.size:
                    if ins.address==base+off and ins.mnemonic=="call": ok=True
                    break
                if ins.address>base+off: break
            if ok: break
        if ok: res.append(base+off)
        if len(res)>=limit: break
    return res
for tgt,name in [(0x7E98F0,"大初始化"),(0x808650,"多人启动封装")]:
    r=find_calls(tgt)
    print("=== 对齐后的 call 0x%08X (%s): %d 个 ==="%(tgt,name,len(r)))
    for va in r: print("   0x%08X"%va)
    print()
