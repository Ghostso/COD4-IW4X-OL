from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
img=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
d=img.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA3A4A..0xBA3A60 (the je at 0xBA3A4F) ===")
for insn in md.disasm(d[0xBA3A4A-BASE:0xBA3A60-BASE], 0xBA3A4A):
    print(f"{insn.address:08X}  {insn.bytes.hex():<16} {insn.mnemonic} {insn.op_str}")
print()
print("bytes @0xBA3A4F:", d[0xBA3A4F-BASE:0xBA3A4F-BASE+2].hex())
