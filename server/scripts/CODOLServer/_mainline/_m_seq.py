from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
# sequential disassembly from the function entry
lo,hi=0xBA3710,0xBA3B00
watch=("- 0x394]","- 0x390]","- 0x3a4]","- 0x3b0]","- 0x3ac]","- 0x39c]")
print("sequential disasm; only lines touching the five slots")
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    o=insn.op_str
    if any(w in o for w in watch):
        kind="WR" if o.startswith("dword ptr [ebp") else ("rd" if o.startswith(("eax,","ecx,","edx,","esi,","ebx,","edi,")) else "??")
        print(f"{insn.address:08X} [{kind}] {insn.mnemonic:<7} {o}")
