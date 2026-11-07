from capstone import Cs, CS_ARCH_X86, CS_MODE_32
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
# 0xBA3AE9 is jne to 0xBA3B0E, 0xBA3B0E is the 0x89 check
# after 0x89 check fails (not 0x89), it goes to 0xBA3B36
o = 0xBA3B0E - BASE
n=0
for ins in md.disasm(d[o:o+0x60], 0xBA3B0E):
    print("0x%08X  %-16s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    n+=1
    if n>20: break
