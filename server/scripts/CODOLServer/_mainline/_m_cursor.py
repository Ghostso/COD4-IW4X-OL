from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== all accesses to [ebp-0x390] in 0xBA3710..0xBA3B00 ===")
lo,hi=0xBA3710,0xBA3B00
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if "- 0x390]" in insn.op_str:
        kind = "WRITE" if insn.op_str.startswith("dword ptr [ebp - 0x390]") else "read/lea"
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}   [{kind}]")
