from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
for name,lo,hi in (("0xBA3FF0",0xBA3FF0,0xBA4040),("0xBA41E0",0xBA41E0,0xBA4230)):
    print(f"=== {name} ===")
    for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
    print()
