from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA3A07..0xBA3A20 (the ebx restore) ===")
for insn in md.disasm(data[0xBA3A07-BASE:0xBA3A20-BASE], 0xBA3A07):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("=== confirm [ebp-0x3ac] and [ebp-0x39c] assignments ===")
lo,hi=0xBA3760,0xBA3780
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
