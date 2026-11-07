import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000
TARGETS = [
    ("0x4F7940 state-commit", 0x004F7940),
    ("0xBA3C05 P4 success",   0x00BA3C05),
    ("0xB783C0 P4 precheck",  0x00B783C0),
]

def main():
    data = open(MEM, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for name, va in TARGETS:
        off = va - BASE
        print("=" * 78)
        print("=== %-24s VA %08X" % (name, va))
        print("=" * 78)
        if off < 0 or off >= len(data):
            print("  OUT OF RANGE")
            print()
            continue
        n = 0
        for ins in md.disasm(data[off:off+0x100], va):
            print("  %08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
            n += 1
            if n >= 28:
                print("  ...")
                break
        print()

if __name__ == "__main__":
    main()
