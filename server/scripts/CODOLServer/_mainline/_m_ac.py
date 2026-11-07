from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== writes to [reg+0xAC] (dword) in 0xBA0000..0xBB0000 ===")
lo,hi=0xBA0000,0xBB0000
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    o=insn.op_str
    if o.startswith("dword ptr [") and "+ 0xac]" in o and insn.mnemonic in ("mov","and","or","add","sub"):
        print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {o}")
