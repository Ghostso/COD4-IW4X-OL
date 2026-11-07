from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
tgt=0x4FD287
# 看 tgt 附近原始字节
o=tgt-base
print("=== 0x4FD287 附近原始字节 ===")
print("  前 32:", d[o-32:o].hex())
print("  本处  :", d[o:o+8].hex())
print()
# 前 32 字节内能否找到合法起点使 tgt 是 call
found=[]
for back in range(1,64):
    st=tgt-back
    ins=list(md.disasm(d[st-base:o+16], st))
    for x in ins:
        if x.address==tgt and x.mnemonic=="call":
            # 该点之前的指令序列必须连续覆盖到 tgt
            covered=st
            ok=True
            for y in ins:
                if y.address!=covered: ok=False; break
                covered=y.address+y.size
                if covered>tgt: break
            if ok: found.append((st,back))
            break
        if x.address>tgt: break
print("可能的起点:", [hex(a) for a,_ in found[:10]])
if found:
    st=found[0][0]
    print()
    print("==== 从 0x%08X 起 ===="%st)
    c=0
    for ins in md.disasm(d[st-base:o+32], st):
        m="  <<< TARGET" if ins.address==tgt else ""
        print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,m)); c+=1
        if c>=30: break
