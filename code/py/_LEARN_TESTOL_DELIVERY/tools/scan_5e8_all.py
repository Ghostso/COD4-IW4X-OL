import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000

def main():
    data = open(MEM, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    print("=== 全量扫[reg+0x5E8]，覆盖 89/C7/8B/8D/FF 等各种 opcode ===")
    pat = struct.pack("<I", 0x5E8)
    seen = set()
    out = []
    i = 0
    n = len(data)
    while i < n - 8:
        if data[i + 2:i + 6] == pat and (data[i + 1] >> 6) == 2:
            start = i - 6
            if start >= 0:
                for ins in md.disasm(data[start:i + 8], BASE + start):
                    if ins.address <= BASE + i < ins.address + ins.size:
                        if ins.address not in seen:
                            seen.add(ins.address)
                            out.append("  %08X  %-22s %s %s" % (
                                ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
                        break
                    if ins.address > BASE + i:
                        break
        i += 1
    for line in sorted(out):
        print(line)
    print("  total = %d" % len(out))

if __name__ == "__main__":
    main()
