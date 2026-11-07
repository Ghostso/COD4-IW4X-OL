from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA3A8D..0xBA3A99 exact bytes ===")
for insn in md.disasm(data[0xBA3A8D-BASE:0xBA3A99-BASE], 0xBA3A8D):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("raw bytes 0xBA3A8D..0xBA3A99:", data[0xBA3A8D-BASE:0xBA3A99-BASE].hex())
