from capstone import *
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
o=0x7F3600-base
print("==== DNS 检查函数 0x007F3600 ====")
c=0
for ins in md.disasm(d[o:o+0x160], 0x7F3600):
    print("  %08X  %-22s %s %s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)); c+=1
    if c>=60: break
