from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000

def dis(data, md, va, n=30, tag=""):
    print("=" * 78)
    print("=== VA %08X  %s" % (va, tag))
    print("=" * 78)
    off = va - BASE
    if off < 0 or off >= len(data):
        print("  OUT OF RANGE"); print(); return
    c = 0
    for ins in md.disasm(data[off:off + 0x160], va):
        mark = ""
        if 0x00BA3C1A <= ins.address <= 0x00BA3C1C:
            mark = "   <<<<< P4"
        print("  %08X  %-22s %s %s%s" % (ins.address, ins.bytes.hex(),
                                          ins.mnemonic, ins.op_str, mark))
        c += 1
        if c >= n:
            print("  ..."); break
    print()

def main():
    data = open(MEM, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    # P4 函数完整（从 0xBA3BA0）
    dis(data, md, 0x00BA3BA0, 34, "P4 function FULL")
    # svc 构造函数
    dis(data, md, 0x00B82130, 24, "svc ctor")
    # 0xC77130
    dis(data, md, 0x00C77130, 14, "0xDE6814 vtable[0]")

if __name__ == "__main__":
    main()
