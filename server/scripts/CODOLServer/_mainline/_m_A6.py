from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== call#1 参数回顾 (0xBA374C..0xBA3794) ===")
for insn in md.disasm(data[0xBA374C-BASE:0xBA379A-BASE], 0xBA374C):
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
print()
print("=== who writes [ebp-0x3a8] ? ===")
lo,hi=0xBA3710,0xBA3B00
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if "- 0x3a8]" in insn.op_str and insn.op_str.startswith("dword ptr [ebp - 0x3a8]"):
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
