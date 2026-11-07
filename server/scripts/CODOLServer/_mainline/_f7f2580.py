from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
def dis(va,n,label):
    o=va-base
    print("==== %s 0x%08X ===="%(label,va)); c=0
    for ins in md.disasm(d[o:o+0x140], va):
        print("  %08X  %-20s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str)); c+=1
        if c>=n: break
dis(0x7F2580, 30, "写状态函数 0x7F2580")
print()
# 找所有 call 0x7F2580 的点
needle = struct.pack("<I", 0x7F2580)
hits=[]; i=base
o=0
while True:
    j=d.find(needle,o)
    if j<0: break
    # 检查前 1 字节是 E8(call)
    if d[j-1]==0xE8:
        hits.append(base+j-4+ (0))
    o=j+1
print("call 0x7F2580 的点（E8 rel32 目标）:")
# proper: scan for E8 rel32 where base+off+5+rel == target
tgt=0x7F2580
res=[]
for off in range(len(d)-5):
    if d[off]==0xE8:
        rel=struct.unpack_from("<i", d, off+1)[0]
        if base+off+5+rel==tgt:
            res.append(base+off)
print("   ", [hex(x) for x in res])
