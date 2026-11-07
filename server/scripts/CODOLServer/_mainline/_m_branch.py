from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA3A50..0xBA3A70 (between dispatch decisions) ===")
for insn in md.disasm(data[0xBA3A50-BASE:0xBA3A70-BASE], 0xBA3A50):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("=== who jumps to 0xBA39E0 / 0xBA39E2 / 0xBA3A65 / 0xBA3A6E ===")
import struct
lo,hi=0xBA3000,0xBA4000
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if insn.mnemonic.startswith("j") and insn.op_str.startswith("0x"):
        t=int(insn.op_str,16)
        if t in (0xBA39E0,0xBA39E2,0xBA3A65,0xBA3A6E,0xBA3A2C,0xBA3A91):
            print(f"{insn.address:08X}  {insn.mnemonic} -> {insn.op_str}")
