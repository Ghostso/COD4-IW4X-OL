from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
def s(va):
    o=va-base
    if o<0 or o>=len(d): return "<out>"
    e=d.find(b"\x00",o)
    return d[o:e].decode("latin1","replace")
print("=== 相关字符串 ===")
for va in (0xDE09E4,0xDE09D0,0xDE09F0,0xDE0A00,0xDE09B8,0xDE09C0):
    print("   0x%08X %r"%(va,s(va)))
print()
md=Cs(CS_ARCH_X86, CS_MODE_32)
o=0x641980-base
print("==== 写 0x81A76A8 的函数 (0x641980 起) ====")
c=0
for ins in md.disasm(d[o:o+0x280], 0x641980):
    mark=""
    if "0x81a76a8" in ins.op_str: mark="   <<<"
    print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,mark)); c+=1
    if c>=85: break
