from capstone import *
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 0x7F26C0 函数完整反汇编（状态机主体）
o=0x7F26C0-base
print("==== 状态机主体 0x7F26C0 ====")
c=0
for ins in md.disasm(d[o:o+0x1C0], 0x7F26C0):
    print("  %08X  %-22s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str)); c+=1
    if c>=95: break
print()
import struct
print("=== 跳转表 @0x7F2850 (6项) ===")
for i in range(6):
    v=struct.unpack_from("<I",d,0x7F2850-base+i*4)[0]
    print("   idx %d (state %d) -> 0x%08X"%(i,i+1,v))
