from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 所有对 0x84ABA50 的引用
le=struct.pack("<I",0x84ABA50)
print("=== 所有引用 0x84ABA50 (state) 的位置 ===")
hits=[]; o=0
while True:
    j=d.find(le,o)
    if j<0: break
    hits.append(base+j); o=j+1
print("共 %d 处"%len(hits))
for va in hits:
    st=max(0,va-base-14)
    ins=list(md.disasm(d[st:va-base+8], base+st))
    # 找那条指令
    last=ins[-3:] if len(ins)>=3 else ins
    print("  --- 0x%08X ---"%va)
    for x in last:
        m="  <<<" if x.address<=va<x.address+x.size else ""
        print("      %08X  %-20s %s %s%s"%(x.address,x.bytes.hex(),x.mnemonic,x.op_str,m))
