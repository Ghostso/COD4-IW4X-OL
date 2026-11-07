from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
# Trace forward from entry: what sets ECX before 0xBA3A42 ?
lo,hi=0xBA3710,0xBA3A46
print("=== every write to ecx / esi / eax in 0xBA3794..0xBA3A45 ===")
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if insn.address < 0xBA3794: continue
    o=insn.op_str; m=insn.mnemonic
    if m in ("mov","lea","xor","add","sub","pop") and o.split(",")[0].strip() in ("ecx","esi","eax","edx","ebx"):
        print(f"{insn.address:08X}  {insn.bytes.hex():<16} {m:<5} {o}")
