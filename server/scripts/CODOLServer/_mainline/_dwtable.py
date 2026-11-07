from capstone import *
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
def dis(va,n,label=""):
    o=va-base
    print("==== %s 0x%08X ===="%(label,va))
    c=0
    for ins in md.disasm(d[o:o+0x200], va):
        print("  %08X  %-20s %s %s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)); c+=1
        if c>=n: break
dis(0x7F2600, 60, "dwLobby 状态名表构建")
print()
dis(0x7F25B0, 25, "取状态函数")
