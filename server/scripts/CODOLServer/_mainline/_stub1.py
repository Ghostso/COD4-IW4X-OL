from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== 0xBA3A99..0xBA3AB5 (where cl / [ebp-0x389] is produced) ===")
for insn in md.disasm(data[0xBA3A99-BASE:0xBA3AB5-BASE], 0xBA3A99):
    print(f"{insn.address:08X}  {insn.bytes.hex():<16} {insn.mnemonic} {insn.op_str}")
print()
print("=== 观察器在采的 obj 偏移（可作落点） ===")
print("  0x5F4 (LOBBY_5E8_READY 附近)  0x600  0x5FC  0x638  0x63C  0x640  0x6D4  0x6D8")
print()
print("=== 需要的最小桩代码（写 1 字节到 edi+0x6d4） ===")
print("  目标：mov [edi+0x6D4], cl     -> 88 8F D4 06 00 00  (6 字节)")
print("  但 0xBA3AA3 处原指令是 mov [ebp-0x389], dl (6 字节)，长度正好")
