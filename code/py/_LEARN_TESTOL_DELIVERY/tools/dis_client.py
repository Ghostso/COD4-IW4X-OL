import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000
TARGETS = [0x4836D0, 0x4F6E0, 0x217A40]

def main():
    with open(MEM, "rb") as f:
        data = f.read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for start in TARGETS:
        off = start - BASE
        if off < 0 or off >= len(data):
            print("=== %08X out of range ===" % start)
            continue
        print("=" * 78)
        print("=== runtime VA %08X (file off %X) ===" % (start, off))
        print("=" * 78)
        blob = data[off:off + 0x110]
        n = 0
        for ins in md.disasm(blob, start):
            cb = ""
            if ins.address == 0x48371A or ins.address == 0x48371B:
                cb = "   <<<<< PATCH TARGET REGION"
            print("  %08X  %-24s %s %s%s" % (
                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, cb))
            n += 1
            if n > 60:
                print("  ... (truncated)")
                break
        print()

if __name__ == "__main__":
    main()
