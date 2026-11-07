import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000

def dis(data, md, va, n=26, tag="", limit=0x140):
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

    dis(data, md, 0x00BA66B0, 26, "svc base ctor (find vtable)")
    dis(data, md, 0x00BA3420, 22, "P4 cleanup method")

    # 读 0xCB7CE0 float
    off = 0x00CB7CE0 - BASE
    if 0 <= off < len(data):
        v = struct.unpack("<f", data[off:off+4])[0]
        print("0xCB7CE0 float = %r (hex %s)" % (v, data[off:off+4].hex(" ")))
    print()

if __name__ == "__main__":
    main()
