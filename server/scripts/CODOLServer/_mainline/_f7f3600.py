from capstone import *
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 完整反汇编 0x7F3600，找所有对 0x84ABA78 的写
o=0x7F3600-base
print("==== 0x7F3600 完整 (DNS 检查) ====")
c=0
for ins in md.disasm(d[o:o+0x300], 0x7F3600):
    mark=""
    if "0x84aba78" in ins.op_str: mark="   <<< 结果变量"
    if "call" in ins.mnemonic: mark+=""
    print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,mark)); c+=1
    if c>=110: break
