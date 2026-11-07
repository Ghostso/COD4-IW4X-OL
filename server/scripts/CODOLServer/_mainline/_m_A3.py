from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== all writes to ebx / ecx between 0xBA3794 and 0xBA3A91 ===")
lo,hi=0xBA379A,0xBA3A92
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if insn.mnemonic=="mov" and insn.op_str.startswith(("ebx,","ecx,")):
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
    elif insn.mnemonic=="lea" and insn.op_str.startswith(("ebx,","ecx,")):
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
