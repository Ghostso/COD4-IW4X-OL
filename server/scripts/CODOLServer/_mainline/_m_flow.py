from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== which jumps reach 0xBA3A2C / 0xBA39E7 ? ===")
lo,hi=0xBA3710,0xBA3B00
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    if insn.mnemonic.startswith("j") and insn.op_str.startswith("0x"):
        t=int(insn.op_str,16)
        if t in (0xBA39E7,0xBA3A2C,0xBA3A65,0xBA3A91,0xBA3AAD):
            print(f"{insn.address:08X}  {insn.mnemonic:<5} -> {insn.op_str}")
print()
print("=== 0xBA38A4..0xBA39E7 : how do we get from the 5EC path to 0xBA39E7 ? ===")
for insn in md.disasm(data[0xBA38A4-BASE:0xBA3920-BASE], 0xBA38A4):
    print(f"{insn.address:08X}  {insn.bytes.hex():<16} {insn.mnemonic} {insn.op_str}")
