# -*- coding: utf-8 -*-
"""P0: 找 vtable +0x140 / +0x13C 的真实调用者。

思路：不只搜固定机器码，而是反汇编全镜像的可执行区间，
识别所有"取 [reg+disp] 到寄存器" 且 disp ∈ {0x140,0x13C} 的指令，
再向后看几条内是否出现 call reg / call [reg]，把这些点全部列出。
"""
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
img = open(IMG, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# 可执行区间（从镜像头看：0x1000..0xE65000 大体可执行）
SCAN_LO = 0x401000
SCAN_HI = 0x400000 + len(img)

DISP_TARGETS = {0x140: "accepted(+0x140)", 0x13C: "timedout(+0x13C)"}


def iter_disp_hits(disp):
    pat = struct.pack("<I", disp)
    s = 0
    while True:
        i = img.find(pat, s)
        if i < 0:
            return
        yield 0x400000 + i
        s = i + 1


def lookback_call(addr):
    """从 addr 向后最多 24 字节，找 call reg / call [reg]。"""
    start = addr - 8
    if start < SCAN_LO:
        return None
    code = img[start - 0x400000: addr - 0x400000 + 0x30]
    for ins in md.disasm(code, start):
        if ins.address <= addr:
            continue
        if ins.mnemonic == "call":
            return "0x%08X  call %s   (disp@0x%08X)" % (ins.address, ins.op_str, addr)
        if ins.address > addr + 24:
            break
    return None


def main():
    for disp, label in sorted(DISP_TARGETS.items()):
        print("=" * 78)
        print("P0: disp=0x%X  (%s)" % (disp, label))
        print("=" * 78)
        total = 0
        for hit in iter_disp_hits(disp):
            # 只看"像取寄存器"的：命中点前 6 字节内应有 8B / FF 前缀
            pre = img[max(0, hit - 0x400000 - 3):hit - 0x400000]
            r = lookback_call(hit)
            total += 1
            if r:
                print("  [CALL] disp@0x%08X  pre=%-8s -> %s"
                      % (hit, pre.hex(), r))
        print("  disp 命中总数 = %d（其中带 call 的已列出）" % total)
        print()


if __name__ == "__main__":
    main()
