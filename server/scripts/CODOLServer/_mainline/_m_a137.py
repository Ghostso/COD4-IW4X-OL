from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
for va in (0xA13774, 0xA1378C):
    print(f"=== {va:08X} ===")
    try:
        for insn in md.disasm(data[va-BASE:va-BASE+48], va):
            print(f"{insn.address:08X}  {insn.bytes.hex():<18} {insn.mnemonic} {insn.op_str}")
    except Exception as e:
        print("  ", e)
    print()
