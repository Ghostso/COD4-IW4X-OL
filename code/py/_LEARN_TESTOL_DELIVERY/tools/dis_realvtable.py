import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000

def dis(data, md, va, n=20, tag="", limit=0x140):
    print("=" * 78)
    print("=== VA %08X  %s" % (va, tag))
    print("=" * 78)
    off = va - BASE
    if off < 0 or off >= len(data):
        print("  OUT OF RANGE"); print(); return
    c = 0
    for ins in md.disasm(data[off:off+limit], va):
        print("  %08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        c += 1
        if c >= n:
            print("  ..."); break
    print()

def main():
    data = open(MEM, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    # 真 vtable 0xD5A5E0
    print("=" * 78)
    print("=== vtable @ 0xD5A5E0 (前 16 项) ===")
    print("=" * 78)
    off = 0xD5A5E0 - BASE
    raw = data[off:off+64]
    for i in range(0, 64, 4):
        v = struct.unpack("<I", raw[i:i+4])[0]
        print("    [%2d] = 0x%08X" % (i//4, v))
    print()

    # 验证 vtable 项是否为合法函数
    for i in (0, 1, 2, 3):
        v = struct.unpack("<I", raw[i*4:i*4+4])[0]
        if 0x400000 <= v < 0xE659000:
            b = data[v-BASE:v-BASE+6]
            print("  [%2d] 0x%08X bytes: %s" % (i, v, b.hex(" ")))

    dis(data, md, 0x00BA0E70, 16, "0xba0e70 (from cleanup)")
    dis(data, md, 0x00BA32A0, 14, "0xba32a0 (from cleanup)")

if __name__ == "__main__":
    main()
