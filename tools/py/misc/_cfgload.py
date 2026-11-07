import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
data = open(IMAGE, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)


def find_entry(va, span=0x600):
    for cand in range(va, va - span, -1):
        off = cand - BASE
        if data[off:off + 3] == b"\x55\x8b\xec":
            return cand
    return None


def disasm(start, end):
    print(f"=== {start:08X}-{end:08X} ===")
    for ins in md.disasm(data[start - BASE:end - BASE], start):
        print(f"{ins.address:08X}  {ins.bytes.hex():<24} {ins.mnemonic} {ins.op_str}")


entry = find_entry(0x50EAB4)
print("function entry containing 0x50EAB4:", hex(entry) if entry else None)
print()
if entry:
    disasm(entry, entry + 0x220)
