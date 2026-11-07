from capstone import Cs, CS_ARCH_X86, CS_MODE_32
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
# 0xBA3600 is the 0x89 handler, 0xBA3590 is 0x87
# The reply parser for 0x85 responses is likely at or near 0xBA0FF0
o = 0xBA0FF0 - BASE
n=0
for ins in md.disasm(d[o:o+0x180], 0xBA0FF0):
    print("0x%08X  %-16s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    n+=1
    if n>50: break
