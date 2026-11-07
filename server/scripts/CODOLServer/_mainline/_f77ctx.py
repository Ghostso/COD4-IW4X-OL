from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
o=0x77F8B3-base
print("==== 0x77F880 .. 0x77F920（call 0x4FD9B0 上下文）====")
c=0
for ins in md.disasm(d[o-0x33:o+0x70], 0x77F880):
    m="  <<< TARGET" if ins.address==0x77F8B3 else ""
    print("  %08X  %-22s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,m)); c+=1
    if c>=45: break
