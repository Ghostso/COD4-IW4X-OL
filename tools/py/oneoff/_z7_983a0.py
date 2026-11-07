from capstone import Cs, CS_ARCH_X86, CS_MODE_32
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
o = 0xB983A0 - BASE
n=0
for ins in md.disasm(d[o:o+0x60], 0xB983A0):
    print("0x%08X  %-18s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    n+=1
    if n>25: break
print()
print("=== 0xB98390 too ===")
o = 0xB98390 - BASE
n=0
for ins in md.disasm(d[o:o+0x30], 0xB98390):
    print("0x%08X  %-18s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    n+=1
    if n>12: break
