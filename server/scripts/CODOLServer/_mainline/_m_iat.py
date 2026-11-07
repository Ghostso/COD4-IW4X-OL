from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
# find all uses of the IAT slot 0xCA8128 in the neighbourhood
import struct
print("=== instructions referencing 0xCA8128 (IAT) ===")
lo,hi=0xB9B000,0xBA4000
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if "0xca8128" in insn.op_str:
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
