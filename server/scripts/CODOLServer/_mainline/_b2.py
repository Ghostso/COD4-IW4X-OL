from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
tgt=0x81A76A8
le=struct.pack("<I",tgt)
print("=== 整镜像内对 0x%08X 的 4 字节引用 ==="%tgt)
hits=[]; o=0
while True:
    j=d.find(le,o)
    if j<0: break
    hits.append(base+j); o=j+1
print("引用点:", [hex(x) for x in hits])
print()
md=Cs(CS_ARCH_X86, CS_MODE_32)
for va in hits:
    # 反汇编前 20 字节看是什么指令
    st=max(0,va-base-16)
    print("--- 0x%08X 上下文 ---"%va)
    for ins in md.disasm(d[st:va-base+12], base+st):
        mark="  <<<" if ins.address<=va<ins.address+ins.size else ""
        print("    %08X  %-20s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,mark))
