from capstone import *
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
base=0x400000
def dis(va, n=60):
    off=va-base
    print("==== VA 0x%08X (off 0x%06X) ===="%(va,off))
    c=0
    for ins in md.disasm(d[off:off+0x120], va):
        print("  %08X  %-20s %s %s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        c+=1
        if c>=n: break
dis(0x007EF0D0, 75)
