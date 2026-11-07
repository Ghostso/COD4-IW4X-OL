import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000

def rd(data, va, n):
    off = va - BASE
    return data[off:off + n] if 0 <= off < len(data) else b""

def dis(data, md, va, n=20, tag=""):
    print("=" * 78)
    print("=== VA %08X  %s" % (va, tag))
    print("=" * 78)
    off = va - BASE
    if off < 0 or off >= len(data):
        print("  OUT OF RANGE"); return
    c = 0
    for ins in md.disasm(data[off:off + 0x100], va):
        print("  %08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        c += 1
        if c >= n:
            print("  ..."); break
    print()

def main():
    data = open(MEM, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    # 1) vtable @ 0xDE6814
    print("=" * 78)
    print("=== vtable @ 0xDE6814 (前 16 个指针) ===")
    print("=" * 78)
    raw = rd(data, 0xDE6814, 64)
    for i in range(0, 64, 4):
        v = struct.unpack("<I", raw[i:i+4])[0]
        print("    vtable[%2d] = 0x%08X" % (i // 4, v))
    print()

    # 2) 0x74C300  LSG 启动候选
    dis(data, md, 0x0074C300, 18, "possible LSG start")
    # 3) 0xB7A400  配置方法
    dis(data, md, 0x00B7A400, 16, "config/reset method")
    # 4) P4 函数入口找 esi 来源：0xBA3C05 前需要找函数开头
    #    函数是 ret 0xC，说明有 3 参数；往前找 push ebp / sub esp
    print("=" * 78)
    print("=== P4 函数入口搜索（0xBA3900..0xBA3C05）===")
    print("=" * 78)
    for va in range(0x00BA3900, 0x00BA3C06, 1):
        b = rd(data, va, 3)
        if len(b) == 3 and b[0] == 0x55 and b[1] == 0x8B and b[2] == 0xEC:
            print("  candidate prologue @ 0x%08X" % va)
    print()

if __name__ == "__main__":
    main()
