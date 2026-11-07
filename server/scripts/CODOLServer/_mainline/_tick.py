from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 找 0x7EFxxx tick 函数的入口
o=0x7EF1C8-base
for delta in range(0,0x120):
    off=o-delta
    if d[off]==0x55 and d[off+1]==0x8B and d[off+2]==0xEC:
        print("tick 函数入口可能是 0x%08X (delta=0x%X)"%(base+off, delta)); break
print()
# 反汇编该函数开头
so=0x7EF0D0-base
print("==== 0x7EF0D0 起 (tick 函数) 前 30 条 ====")
c=0
for ins in md.disasm(d[so:so+0x100], 0x7EF0D0):
    print("  %08X  %-22s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str)); c+=1
    if c>=28: break
print()
# 谁调用 0x7EF0D0
res=[]
for off in range(len(d)-5):
    if d[off]==0xE8:
        rel=struct.unpack_from("<i", d, off+1)[0]
        if base+off+5+rel==0x7EF0D0: res.append(base+off)
print("=== call 0x7EF0D0 的调用者 ===")
for va in res[:10]: print("   0x%08X"%va)
print("   total=%d"%len(res))
