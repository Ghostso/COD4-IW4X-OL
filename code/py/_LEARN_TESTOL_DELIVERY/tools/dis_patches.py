import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000

# nt10.py 的 4 个补丁点（报告 042 提取）
PATCHES = [
    ("P1 UnsignedAuthGate",      0x00B9A78C),
    ("P2 UnsignedClientTicket",  0x00B9A7B0),
    ("P3 AuthParseFallback",     0x00B9A7B0),
    ("P3 target",                0x00B9A7F1),
    ("P4 LocalLsgNonceCheck",    0x00BA3C1A),
    ("EXT UnsignedFastFiles",    0x0048371A),
]

def main():
    with open(MEM, "rb") as f:
        data = f.read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for name, va in PATCHES:
        off = va - BASE
        print("=" * 78)
        print("=== %-26s VA %08X  (file off %X)" % (name, va, off))
        print("=" * 78)
        if off < 0 or off >= len(data):
            print("  OUT OF RANGE")
            print()
            continue
        print("  raw 24 bytes: %s" % data[off:off+24].hex(" "))
        print("  disasm:")
        n = 0
        for ins in md.disasm(data[off:off+0x60], va):
            print("    %08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
            n += 1
            if n >= 14:
                print("    ...")
                break
        print()

if __name__ == "__main__":
    main()
