from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA39E0..0xBA3A30 (provider call + inner read setup) ===")
for insn in md.disasm(data[0xBA39E0-BASE:0xBA3A30-BASE], 0xBA39E0):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
