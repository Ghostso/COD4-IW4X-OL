from capstone import *
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
o=0x7F34E0-base
print("==== 0x007F34E0 (DNS 判定核心) ====")
c=0
for ins in md.disasm(d[o:o+0x120], 0x7F34E0):
    print("  %08X  %-22s %s %s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)); c+=1
    if c>=52: break
print()
# 相关字符串/全局
import struct
def s(va):
    oo=va-base
    if oo<0 or oo>=len(d): return "<out>"
    e=d.find(b"\x00",oo); return d[oo:e].decode("latin1","replace")
print("=== 涉及的全局对象 ===")
for va in (0x84ABA70,0x84ABA74,0x84ABA78,0x84ABA50,0x84ABA48):
    v=struct.unpack_from("<I",d,va-base)[0] if 0<=va-base<len(d)-4 else None
    print("  0x%08X = 0x%X"%(va,v if v is not None else 0))
