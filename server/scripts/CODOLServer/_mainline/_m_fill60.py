from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA1E30..0xBA1E60 (the fill of [ebp-0x60]) ===")
lo,hi=0xBA1E30,0xBA1E60
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("=== 0xC73D20 head ===")
lo,hi=0xC73D20,0xC73D90
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
