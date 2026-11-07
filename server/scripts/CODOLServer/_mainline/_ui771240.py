from capstone import *
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 反汇编 0x771240 (UI 投递函数) 前 80 条
o=0x771240-base
print("==== 0x771240 (面板投递) ====")
c=0
for ins in md.disasm(d[o:o+0x160], 0x771240):
    print("  %08X  %-22s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str)); c+=1
    if c>=70: break
