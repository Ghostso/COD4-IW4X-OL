#!/usr/bin/env python3
"""扫描镜像中所有 "写 [reg+4] = 立即数" 的指令，候选 = dwRoomMessage 类型号。

构造函数的典型形态（MSVC /O2）:
  mov  dword ptr [ecx + 4], 0xNN   -> c7 41 04 NN 00 00 00
  mov  byte  ptr [ecx + 4], 0xNN   -> c6 41 04 NN
  mov  dword ptr [eax + 4], 0xNN   -> c7 40 04 NN 00 00 00
  mov  byte  ptr [eax + 4], 0xNN   -> c6 40 04 NN

用法: python -I tools/msgtype_scan.py
输出: VA, 指令原文, 立即数
"""
import sys

import capstone.x86 as X
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

DUMP = ("CODOL_LOCAL_ENGINE_CHAIN_20261019/logs/"
        "ROUND2_STATIC_DUMP_20261019_203103/client_runtime.bin")
BASE = 0x400000

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def main():
    b = open(DUMP, "rb").read()
    lo, hi = 0x624000 - BASE, 0x640000 - BASE
    md.skipdata = True
    hits = []
    for ins in md.disasm(b[lo:hi], 0x624000):
        if ins.mnemonic != "mov" or len(ins.operands) != 2:
            continue
        dst, src = ins.operands
        if dst.type != X.X86_OP_MEM or src.type != X.X86_OP_IMM:
            continue
        if dst.mem.disp != 4:
            continue
        base = dst.mem.base
        if base == 0:
            continue
        # 必须是 dword 或 byte 写
        size = dst.size
        if size not in (1, 4):
            continue
        hits.append((ins.address, size, src.imm, ins.op_str,
                     md.reg_name(base)))
    print("共 %d 处写 [reg+4]" % len(hits))
    print("%-12s %-6s %-12s %s" % ("VA", "宽度", "立即数", "指令"))
    for va, size, imm, txt, rg in hits:
        print("%#010x %-6d %-12d %s" % (va, size, imm, txt))
    # 按立即数统计
    from collections import Counter
    c = Counter(imm for _, _, imm, _, _ in hits if 0 <= imm <= 0xFF)
    print("\n=== 立即数(0..255) 频次 ===")
    for k, n in sorted(c.items()):
        print("  %3d (0x%02x) × %d" % (k, k, n))


if __name__ == "__main__":
    main()
