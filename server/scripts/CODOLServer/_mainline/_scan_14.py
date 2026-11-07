from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG = Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
BASE = 0x400000
data = IMG.read_bytes()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
hits=[]
for insn in md.disasm(data, BASE):
    ops = insn.op_str
    if "+ 0x14]" not in ops: continue
    if not ops.startswith("dword ptr ["): continue
    if insn.mnemonic not in ("mov",): continue
    # destination is the first operand
    if not ops.split(",")[0].strip().startswith("dword ptr ["): continue
    hits.append(insn)
print("total mov [reg+0x14], X :", len(hits))
for i in hits[:40]:
    print(f"  {i.address:08X}  {i.bytes.hex():<16} {i.mnemonic} {i.op_str}")
