from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
# scan for writes to [reg+0x644]
print("--- insns writing [reg+0x644] ---")
lo,hi=0xBA0000,0xBB0000
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    ops=insn.op_str
    if "+ 0x644]" not in ops: continue
    if insn.mnemonic not in ("mov","and","or"): continue
    if not ops.split(",")[0].strip().startswith("dword ptr ["): continue
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
