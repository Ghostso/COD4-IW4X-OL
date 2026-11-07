from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== writes to [ebp-0x3ac] and [ebp-0x3a4] in 0xBA3700..0xBA3B00 ===")
for insn in md.disasm(data[0xBA3700-BASE:0xBA3B00-BASE], 0xBA3700):
    ops=insn.op_str
    if ("- 0x3ac]" in ops or "- 0x3a4]" in ops) and ops.split(",")[0].strip().endswith("]"):
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("=== reads of [ebp-0x3ac] / [ebp-0x3a4] ===")
for insn in md.disasm(data[0xBA3700-BASE:0xBA3B00-BASE], 0xBA3700):
    ops=insn.op_str
    if ("- 0x3ac]" in ops or "- 0x3a4]" in ops) and not ops.split(",")[0].strip().endswith("]"):
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
