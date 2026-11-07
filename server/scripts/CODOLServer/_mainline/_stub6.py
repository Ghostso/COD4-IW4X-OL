from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
img=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
d=img.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA3AD8..0xBA3AEC (the reader of [ebp-0x389]) ===")
for insn in md.disasm(d[0xBA3AD8-BASE:0xBA3AEC-BASE], 0xBA3AD8):
    print(f"{insn.address:08X}  {insn.bytes.hex():<16} {insn.mnemonic} {insn.op_str}")
print()
print("bytes at 0xBA3AE0:", d[0xBA3AE0-BASE:0xBA3AE0-BASE+6].hex())
print("bytes at 0xBA3AA3:", d[0xBA3AA3-BASE:0xBA3AA3-BASE+6].hex())
print()
print("plan:")
print("  0xBA3AA3: 88 95 77 FC FF FF  ->  88 97 D4 06 00 00   (mov [edi+0x6D4], dl)")
print("  0xBA3AE0: 8A 8D 77 FC FF FF  ->  8A 8F D4 06 00 00   (mov cl, [edi+0x6D4])")
print("  both 6 bytes, equal length, no jump needed.")
