from capstone import *
import struct, re
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 找 0x641980 函数的入口（往前找 prologue）
o=0x641980-base
# 找函数头
start=None
for delta in range(0,0x200):
    off=o-delta
    if d[off]==0x55 and d[off+1]==0x8B and d[off+2]==0xEC:
        start=base+off; break
print("函数入口可能在 0x%08X"%(start or 0))
# 看 0x641980 之前谁调用它
print()
print("=== 0x641900..0x641980 反汇编 ===")
o2=0x641900-base
c=0
for ins in md.disasm(d[o2:o2+0x90], 0x641900):
    print("  %08X  %-22s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str)); c+=1
    if c>=40: break
