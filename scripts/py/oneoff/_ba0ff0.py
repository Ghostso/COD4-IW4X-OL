import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
data = open(IMAGE, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)


def disasm(start, end):
    print(f"=== {start:08X}-{end:08X} ===")
    for ins in md.disasm(data[start - BASE:end - BASE], start):
        print(f"{ins.address:08X}  {ins.bytes.hex():<24} {ins.mnemonic} {ins.op_str}")


disasm(0xBA0FF0, 0xBA1200)
print()
disasm(0xBA3590, 0xBA3720)
