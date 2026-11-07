import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000
TARGETS = [
    ("P4 jump target 0xBA3C62", 0x00BA3C62),
    ("P1 target 0xBA3C0x region", 0x00BA3BC0),
    ("P1 alt target 0xB9A742",   0x00B9A742),
]

def main():
    data = open(MEM, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for name, va in TARGETS:
        off = va - BASE
        print("=" * 78)
        print("=== %-28s VA %08X" % (name, va))
        print("=" * 78)
        if off < 0 or off >= len(data):
            print("  OUT OF RANGE")
            print()
            continue
        n = 0
        for ins in md.disasm(data[off:off+0x80], va):
            print("  %08X  %-20s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
            n += 1
            if n >= 20:
                break
        print()

if __name__ == "__main__":
    main()
