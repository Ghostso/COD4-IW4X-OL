from capstone import Cs, CS_ARCH_X86, CS_MODE_32
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
# '8d 8d 38 fd ff ff' = lea ecx,[ebp-0x2c8] — find the exact offset
import re
o_all = 0xB9A540 - BASE
seg = d[o_all:o_all+0x40]
i = seg.find(b"\x8d\x8d\x38\xfd\xff\xff")
print("pattern at file off:", hex(o_all+i), "VA:", hex(0xB9A540+i))
start = 0xB9A540 + i
o = start - BASE
n=0
for ins in md.disasm(d[o:o+0x130], start):
    print("0x%08X  %-18s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    n+=1
    if n>45: break
