from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
img=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
d=img.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 候选打标记点（等长可替换）===")
for lo,hi in [(0xBA39E7,0xBA39F8),(0xBA3A18,0xBA3A28),(0xBA3A51,0xBA3A5D)]:
    print("---")
    for insn in md.disasm(d[lo-BASE:hi-BASE], lo):
        print(f"{insn.address:08X}  {insn.bytes.hex():<16} {insn.mnemonic} {insn.op_str}")
