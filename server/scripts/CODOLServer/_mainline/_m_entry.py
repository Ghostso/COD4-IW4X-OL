from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
# scan back for the prologue of this function (push ebp / mov ebp,esp)
print("=== 0xBA3600..0xBA3760 ===")
for insn in md.disasm(data[0xBA3600-BASE:0xBA3760-BASE], 0xBA3600):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
