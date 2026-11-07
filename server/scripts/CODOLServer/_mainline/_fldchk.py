from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
for off in ("0x5e0","0xa8","0x6dc","0x6d8"):
    print("=== obj+%s 的所有访问（全镜像 0xBA0000-0xBB0000） ===" % off)
    lo,hi=0xBA0000,0xBB0000
    n=0
    for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
        if ("+ %s]" % off) in insn.op_str:
            print("   0x%08X  %s %s" % (insn.address, insn.mnemonic, insn.op_str))
            n+=1
            if n>8: print("   ..."); break
    if n==0: print("   (无访问)")
    print()
