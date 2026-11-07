from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
img=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
d=img.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA3A18..0xBA3A4F 之间所有跳转 ===")
for insn in md.disasm(d[0xBA3A18-BASE:0xBA3A50-BASE], 0xBA3A18):
    m=insn.mnemonic
    mark = "   <<<" if m.startswith("j") or m=="call" else ""
    print(f"{insn.address:08X}  {insn.bytes.hex():<16} {m} {insn.op_str}{mark}")
