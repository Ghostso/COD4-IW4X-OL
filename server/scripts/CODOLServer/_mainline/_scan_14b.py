from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG = Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data = IMG.read_bytes(); BASE=0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata=True
groups={}
for insn in md.disasm(data, BASE):
    ops=insn.op_str; m=insn.mnemonic
    if not ops.split(",")[0].strip().startswith(("byte ptr [","xmmword ptr [")): continue
    if m not in ("mov","movups","movdqu","movaps","movdqa","movss"): continue
    if "+ 0x14]" in ops:
        groups.setdefault(m+" "+ops.split(",")[0].strip()[:14], []).append(insn.address)
for k,v in sorted(groups.items(), key=lambda x:-len(x[1]))[:15]:
    print(f"{len(v):5d}  {k}   e.g. " + ", ".join("%08X"%a for a in v[:4]))
