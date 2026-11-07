from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA3A60..0xBA3AB0 (full control flow) ===")
for insn in md.disasm(data[0xBA3A62-BASE:0xBA3AB0-BASE], 0xBA3A62):
    m = insn.mnemonic
    mark = "   <<<" if (m in ("je","jne","ja","jbe","jmp","call") ) else ""
    print(f"{insn.address:08X}  {insn.bytes.hex():<18} {m} {insn.op_str}{mark}")
