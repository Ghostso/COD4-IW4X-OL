from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
print("raw bytes 0xBA3A48..0xBA3A70:")
b=data[0xBA3A48-BASE:0xBA3A70-BASE]
print(" ", b.hex())
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print()
for start in (0xBA3A48,0xBA3A4A,0xBA3A4C,0xBA3A4E):
    print(f"--- disasm from {start:08X} ---")
    for insn in md.disasm(data[start-BASE:start-BASE+0x28], start):
        print(f"  {insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
    print()
