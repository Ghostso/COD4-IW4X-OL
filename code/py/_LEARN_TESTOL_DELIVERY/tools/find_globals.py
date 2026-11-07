import sys, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000
WATCH = 0x082CA530          # 全局 LSG 状态
WATCH2 = 0x08269774         # 记忆里的 svc 槽

def main():
    data = open(MEM, "rb").read()
    print("mem size = %d (0x%X)" % (len(data), len(data)))

    # 1) 原始字节搜索：立即数出现位置（disp32 或 imm32）
    for name, val in (("0x82CA530", WATCH), ("0x8269774", WATCH2)):
        pat = struct.pack("<I", val)
        hits = []
        i = data.find(pat)
        while i >= 0 and len(hits) < 40:
            hits.append(i)
            i = data.find(pat, i + 1)
        print("\n=== %s (LE bytes %s) : %d hits ===" % (name, pat.hex(" "), len(hits)))
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        for h in hits:
            # 从命中位置往回 8 字节开始反汇编，看能否落到该指令
            start = h - 8
            if start < 0:
                continue
            shown = False
            for ins in md.disasm(data[start:h + 8], BASE + start):
                if ins.address <= BASE + h < ins.address + ins.size:
                    print("  %08X  %-24s %s %s" % (
                        ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
                    shown = True
                    break
                if ins.address > BASE + h:
                    break
            if not shown:
                print("  (hit @ off %X, not decoded)" % h)

if __name__ == "__main__":
    main()
