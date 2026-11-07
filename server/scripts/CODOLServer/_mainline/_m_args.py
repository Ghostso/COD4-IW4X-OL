from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
lo,hi=0xBA1E6B,0xBA1E9E
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("--- 0xBA05A0 entry arg usage ---")
lo,hi=0xBA05A0,0xBA05C0
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
