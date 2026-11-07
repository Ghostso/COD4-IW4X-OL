from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
# scan the whole enclosing function for references to [ebp-0x60]
lo,hi=0xBA1800,0xBA1E80
print("--- insns mentioning ebp - 0x60 ---")
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if "- 0x60]" in insn.op_str:
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("--- insns writing to [ebp-0x4f4 .. ] via 0xb78350 results ---")
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if insn.mnemonic=="call" and insn.op_str=="0xb78350":
        print(f"  read-call at {insn.address:08X}")
