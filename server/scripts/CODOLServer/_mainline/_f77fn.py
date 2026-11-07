from capstone import *
import struct, re
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
o=0x77F8B3-base
ent=None
for k in range(1,0x700):
    off=o-k
    if d[off]==0xCC and d[off+1]==0xCC and d[off+2]==0xCC:
        ent=base+off+1
        while d[ent-base]==0xCC: ent+=1
        break
print("函数入口 0x%08X"%ent)
strs={}
for m in re.finditer(rb"[\x20-\x7e]{4,}", d):
    strs[base+m.start()]=m.group().decode("latin1")
def hint(ops):
    for v,t in strs.items():
        if ("0x%x"%v) in ops: return "  ; \"%s\""%t[:60]
    return ""
so=ent-base; c=0
print("==== 入口起 90 条 ====")
for ins in md.disasm(d[so:so+0x300], ent):
    m="  <<< call 0x4FD9B0" if ins.address==0x77F8B3 else ""
    print("  %08X  %-22s %s %s%s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,hint(ins.op_str),m)); c+=1
    if c>=90: break
