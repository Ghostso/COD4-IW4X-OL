from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== any instruction in 0xBA39E7..0xBA3A2C touching [ebp-0x50] ===")
found=False
for insn in md.disasm(data[0xBA39E7-BASE:0xBA3A2C-BASE], 0xBA39E7):
    if "0x50]" in insn.op_str:
        print(f"  {insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
        found=True
if not found: print("  (none)")
print()
print("=== who ELSE writes [ebp-0x50] in the whole 0xBA3700..0xBA3B00 ===")
for insn in md.disasm(data[0xBA3700-BASE:0xBA3B00-BASE], 0xBA3700):
    ops=insn.op_str
    if "- 0x50]" in ops and ops.split(",")[0].strip().endswith("]"):
        print(f"  {insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("=== who reads [ebp-0x50] ===")
for insn in md.disasm(data[0xBA3700-BASE:0xBA3B00-BASE], 0xBA3700):
    ops=insn.op_str
    if "- 0x50]" in ops and ops.split(",")[0].strip().endswith("]"):
        pass
    if "- 0x50]" in ops and not ops.split(",")[0].strip().endswith("]"):
        print(f"  {insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
