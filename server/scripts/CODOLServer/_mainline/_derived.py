from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
o=0x7F25B0-base
print("==== 0x7F25B0 (派生状态) 完整 ====")
c=0
for ins in md.disasm(d[o:o+0x60], 0x7F25B0):
    print("  %08X  %-22s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str)); c+=1
    if c>=22: break
print()
print("=== 跳转表 @0x7F25DC (state 0..5) ===")
for i in range(6):
    v=struct.unpack_from("<I",d,0x7F25DC-base+i*4)[0]
    print("   state %d -> 0x%08X"%(i,v))
print()
# 看每个目标返回什么
for i in range(6):
    v=struct.unpack_from("<I",d,0x7F25DC-base+i*4)[0]
    if 0x400000<=v<base+len(d):
        oo=v-base
        ins=list(md.disasm(d[oo:oo+16], v))[:4]
        print("   state %d -> 0x%08X : %s"%(i,v," | ".join("%s %s"%(x.mnemonic,x.op_str) for x in ins)))
    else:
        print("   state %d -> 0x%08X : (越界/数据)"%(i,v))
