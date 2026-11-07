from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA35E0..0xBA35F0 exact bytes ===")
for insn in md.disasm(data[0xBA35E0-BASE:0xBA35F0-BASE], 0xBA35E0):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("=== 0xBA35C1 (fail exit) ===")
for insn in md.disasm(data[0xBA35C1-BASE:0xBA35D0-BASE], 0xBA35C1):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
