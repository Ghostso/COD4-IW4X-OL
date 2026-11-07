from capstone import Cs, CS_ARCH_X86, CS_MODE_32
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
o = 0xB9A548 - BASE
n = 0
for ins in md.disasm(d[o:o+0x120], 0xB9A548):
    print("0x%08X  %-18s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    n += 1
    if n > 45: break
if n == 0:
    print("(no output — check offset)")
    print("bytes at 0xB9A548:", d[o:o+16].hex(" "))
