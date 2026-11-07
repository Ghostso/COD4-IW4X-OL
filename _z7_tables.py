from capstone import Cs, CS_ARCH_X86, CS_MODE_32
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
# dump the two table initializations fully
o = 0x80399A - BASE
n=0
for ins in md.disasm(d[o:o+0x560], 0x80399A):
    if ins.mnemonic=="mov" and ins.op_str.startswith("dword ptr [ebp"):
        print("0x%08X  %s" % (ins.address, ins.op_str))
        n+=1
    if n>60: break
