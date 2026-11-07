from capstone import Cs, CS_ARCH_X86, CS_MODE_32
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
o = 0x803C00 - BASE
n=0
start=None
for ins in md.disasm(d[o:o+0x400], 0x803C00):
    if ins.mnemonic=="push" and ins.op_str=="ebp":
        # check next is mov ebp,esp
        start = ins.address
    if start and ins.address > start and ins.address < start+4:
        pass
    n+=1
print("(scan done)")
# simpler: print around 0x803E60
n=0
for ins in md.disasm(d[0x803E50-BASE:0x803E50-BASE+0xA0], 0x803E50):
    print("0x%08X  %-16s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    n+=1
    if n>25: break
