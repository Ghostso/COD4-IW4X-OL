from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== ALL instructions mentioning esi between 0xBA39E7 and 0xBA3A5D ===")
lo,hi=0xBA39E7,0xBA3A5E
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if "esi" in insn.op_str or insn.mnemonic in ("pusha","popa","push","pop"):
        print(f"{insn.address:08X}  {insn.bytes.hex():<16} {insn.mnemonic} {insn.op_str}")
print()
print("=== also: does the provider call (0xBA3A05) preserve esi? (cdecl: callee must) ===")
print("callee 0xC73C10 -- check for esi save/restore at its entry/exit")
lo,hi=0xC73C10,0xC73C70
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    print(f"{insn.address:08X}  {insn.bytes.hex():<16} {insn.mnemonic} {insn.op_str}")
