from capstone import Cs, CS_ARCH_X86, CS_MODE_32
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
# 0xBA11E2 onwards: after reading u16 len, start reading payload
o = 0xBA11E2 - BASE
n=0
for ins in md.disasm(d[o:o+0x100], 0xBA11E2):
    print("0x%08X  %-16s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    n+=1
    if n>40: break
