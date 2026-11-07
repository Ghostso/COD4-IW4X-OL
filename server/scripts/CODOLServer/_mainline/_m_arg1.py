from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA35D0..0xBA35F0 (0xBA3010 call site) ===")
for insn in md.disasm(data[0xBA35D0-BASE:0xBA35F0-BASE], 0xBA35D0):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("=== 0xBA3590 head (arg usage) ===")
for insn in md.disasm(data[0xBA3590-BASE:0xBA35B0-BASE], 0xBA3590):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("=== caller of 0xBA3590 (0xBA3B02) context ===")
for insn in md.disasm(data[0xBA3AE0-BASE:0xBA3B10-BASE], 0xBA3AE0):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
