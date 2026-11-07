from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 从多个候选起点反汇编，找能连续覆盖到 0x4FD287 的
tgto=0x4FD287-base
for st in range(0x4FD200,0x4FD288):
    ins=list(md.disasm(d[st-base:tgto+8], st))
    cov=st; ok=True
    for x in ins:
        if x.address!=cov: ok=False; break
        cov=x.address+x.size
        if cov>0x4FD287: break
    if ok and cov>=0x4FD287+5:
        print("可用起点 0x%08X"%st); print()
        c=0
        for x in md.disasm(d[st-base:tgto+40], st):
            m="  <<< TARGET" if x.address==0x4FD287 else ""
            print("  %08X  %-20s %s %s%s"%(x.address,x.bytes.hex(),x.mnemonic,x.op_str,m)); c+=1
            if c>=40: break
        break
