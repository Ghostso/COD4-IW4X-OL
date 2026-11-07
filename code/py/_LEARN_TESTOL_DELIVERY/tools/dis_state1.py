from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000

def dis(data, md, va, n=22, tag="", lead=0x28):
    print("=" * 78)
    print("=== VA %08X  %s" % (va, tag))
    print("=" * 78)
    start = va - lead
    off = start - BASE
    if off < 0 or off >= len(data):
        print("  OUT OF RANGE"); print(); return
    c = 0
    for ins in md.disasm(data[off:off + 0x140], start):
        mark = "   <<<<<" if va <= ins.address <= va + 4 else ""
        print("  %08X  %-22s %s %s%s" % (ins.address, ins.bytes.hex(),
                                          ins.mnemonic, ins.op_str, mark))
        c += 1
        if c >= n:
            print("  ..."); break
    print()

def main():
    data = open(MEM, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    dis(data, md, 0x00B83920, 20, "byte write state=1")
    dis(data, md, 0x00BA07A6, 16, "cmp ==3 (A)")
    dis(data, md, 0x00BA2B6A, 16, "cmp ==3 (B)")
    dis(data, md, 0x00BA34E6, 18, "cmp ==3 (C)")

if __name__ == "__main__":
    main()
