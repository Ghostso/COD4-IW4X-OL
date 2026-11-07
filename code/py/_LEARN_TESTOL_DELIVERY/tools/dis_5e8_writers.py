from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000

def dis(data, md, va, n=24, tag="", lead=0x20):
    print("=" * 78)
    print("=== VA %08X  %s" % (va, tag))
    print("=" * 78)
    start = va - lead
    off = start - BASE
    if off < 0 or off >= len(data):
        print("  OUT OF RANGE"); print(); return
    c = 0
    for ins in md.disasm(data[off:off + 0x120], start):
        mark = ""
        if va <= ins.address <= va + 3:
            mark = "   <<<<< TARGET"
        print("  %08X  %-22s %s %s%s" % (ins.address, ins.bytes.hex(),
                                          ins.mnemonic, ins.op_str, mark))
        c += 1
        if c >= n:
            print("  ..."); break
    print()

def main():
    data = open(MEM, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    dis(data, md, 0x006E1246, 22, "write 0x5E8 = edi")
    dis(data, md, 0x006F42FB, 22, "write 0x5E8 = ebx")
    dis(data, md, 0x00BA2984, 22, "write 0x5E8 = ebx (BA family)")
    dis(data, md, 0x00BA44E8, 18, "read 0x5E8 (BA family)")

if __name__ == "__main__":
    main()
