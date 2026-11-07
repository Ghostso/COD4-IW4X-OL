import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000

def dis(data, md, va, n=22, tag=""):
    off = va - BASE
    print("=" * 78)
    print("=== VA %08X  %s" % (va, tag))
    print("=" * 78)
    if off < 0 or off >= len(data):
        print("  OUT OF RANGE")
        return
    c = 0
    for ins in md.disasm(data[off:off + 0x120], va):
        print("  %08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        c += 1
        if c >= n:
            print("  ...")
            break
    print()

def main():
    data = open(MEM, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    dis(data, md, 0x008036C0, 20, "svc cmp/lifecycle")
    dis(data, md, 0x0077D060, 22, "svc write site 0x77D086")
    dis(data, md, 0x004F8545, 18, "svc read site")
    dis(data, md, 0x00803830, 24, "svc write 0x803851/0x80388E")

    # 搜 [reg + 0x4F4] 形式：8B 8? F4 04 00 00 / 8B 9? F4 04 00 00 ...
    print("=" * 78)
    print("=== 搜 sub 偏移 0x4F4 (1268) 的访问 ===")
    print("=" * 78)
    targets = []
    for i in range(len(data) - 7):
        # 8B /r with disp32 = F4 04 00 00
        if data[i] in (0x8B, 0x89) and data[i+2:i+6] == b"\xf4\x04\x00\x00":
            targets.append(i)
            if len(targets) >= 20:
                break
    for h in targets:
        start = h - 4
        if start < 0:
            continue
        for ins in md.disasm(data[start:h + 8], BASE + start):
            if ins.address <= BASE + h < ins.address + ins.size:
                print("  %08X  %-22s %s %s" % (ins.address, ins.bytes.hex(),
                                                ins.mnemonic, ins.op_str))
                break
            if ins.address > BASE + h:
                break
    print("\n  total hits (capped) = %d" % len(targets))

if __name__ == "__main__":
    main()
