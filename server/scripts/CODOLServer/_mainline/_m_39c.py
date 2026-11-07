from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== all writes/reads of [ebp-0x39c] in 0xBA3700..0xBA3B00 ===")
lo,hi=0xBA3700,0xBA3B00
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if "- 0x39c]" in insn.op_str:
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("=== also [ebp-0x3b0] and [ebp-0x3ac] and [ebp-0x390] ===")
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    for off in ("- 0x3b0]","- 0x3ac]","- 0x390]"):
        if off in insn.op_str:
            print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
            break
