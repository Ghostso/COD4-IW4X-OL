from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
o=0x4FD230-base
print("==== 0x4FD230 .. 0x4FD2C0 ====")
c=0
for ins in md.disasm(d[o:o+0x90], 0x4FD230):
    m="  <<< call 0x808650" if ins.address==0x4FD287 else ""
    print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,m)); c+=1
    if c>=40: break
print()
# 该点前 200 字节内的字符串引用
import re
strs={}
for s in __import__("pefile").PE(p).sections:
    pass
