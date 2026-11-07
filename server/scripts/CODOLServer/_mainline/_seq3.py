from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
img=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
d=img.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA3A51..0xBA3AB0 (full sequence after the 0xBA3A4F je) ===")
for insn in md.disasm(d[0xBA3A51-BASE:0xBA3AB0-BASE], 0xBA3A51):
    print(f"{insn.address:08X}  {insn.bytes.hex():<16} {insn.mnemonic} {insn.op_str}")
