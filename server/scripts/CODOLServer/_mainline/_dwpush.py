from capstone import *
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
o=0x7F2680-base
print("==== 0x007F2680 (状态推进函数) ====")
c=0
for ins in md.disasm(d[o:o+0x1D0], 0x7F2680):
    print("  %08X  %-22s %s %s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)); c+=1
    if c>=72: break
print()
print("=== 相关字符串 ===")
def s(va):
    oo=va-base
    if oo<0 or oo>=len(d): return "<out>"
    e=d.find(b"\x00",oo); return d[oo:e].decode("latin1","replace")
for va in (0xDE08C8,0xDE08D8,0xDE08E8,0xDE08F8,0xDE090C,0xDE0928,0xDE0938,0xDE098C,0xDE0610,0xDE0640):
    print("  0x%08X %r"%(va,s(va)))
