from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
# find the prologue of the function containing 0xBA46C2 by scanning back
print("=== scanning back from 0xBA46C2 for a prologue ===")
lo,hi=0xBA43A0,0xBA44A0
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
