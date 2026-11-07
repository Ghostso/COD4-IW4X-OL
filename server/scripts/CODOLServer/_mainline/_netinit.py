from capstone import *
import re, struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 收集整镜像可读字符串 VA 表（用于标注 push 的字符串）
strs={}
for m in re.finditer(rb"[\x20-\x7e]{4,}", d):
    strs[base+m.start()]=m.group().decode("latin1")
def hint(ops):
    for v,t in strs.items():
        if ("0x%x"%v) in ops: return "  ; \"%s\""%t[:70]
    return ""
o=0x808650-base
print("==== 0x808650 全套联网初始化 (前 110 条) ====")
c=0
for ins in md.disasm(d[o:o+0x400], 0x808650):
    print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,hint(ins.op_str))); c+=1
    if c>=110: break
