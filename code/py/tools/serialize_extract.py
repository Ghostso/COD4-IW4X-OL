#!/usr/bin/env python3
"""自动提取 serialize 函数的位流写入序列。

扫描函数体内对 0xb77b10(writeBits) / 0xb777c0(writeData) 的调用，
把紧邻的 push 参数解析出来，输出近似"写入脚本"。
"""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000
WRITEBITS = 0xB77B10
WRITEDATA = 0xB777C0

NAMES = {
    0x0E59D20: "[模式]", 0x08269774: "[连接单例]",
}


def main():
    va = int(sys.argv[1], 0)
    n = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x120
    b = open(DUMP, "rb").read()
    o = va - BASE
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    pend = []      # 最近的 push 立即数/说明
    for ins in md.disasm(b[o:o + n], va):
        if ins.id == 0:
            continue
        m, ops = ins.mnemonic, ins.operands
        if m == "push":
            if ops[0].type == 2:
                imm = ops[0].imm
                tag = NAMES.get(imm)
                pend.append("imm:%#x%s" % (imm, ("(" + tag + ")") if tag else ""))
            elif ops[0].type == 3:
                disp = ops[0].mem.disp
                base = ins.reg_name(ops[0].mem.base)
                pend.append("[%s+%#x]" % (base, disp) if disp else "[%s]" % base)
            else:
                pend.append(ins.reg_name(ops[0].reg))
            if len(pend) > 6:
                pend.pop(0)
            continue
        if m == "call" and ops[0].type == 2:
            tgt = ops[0].imm
            if tgt == WRITEBITS:
                # 上一个 push 是位宽
                w = pend[-1] if pend else "?"
                print("  %#010x  writeBits(%-28s)" % (ins.address, w))
                pend = []
            elif tgt == WRITEDATA:
                # push nbits ; push ptr ; (ecx=writer)
                nbits = pend[-2] if len(pend) >= 2 else "?"
                ptr = pend[-1] if pend else "?"
                print("  %#010x  writeData(%-24s, %s)" % (ins.address, ptr, nbits))
                pend = []
            elif tgt == 0x0C427F0 or tgt == 0x0C74510:
                pend = []
            else:
                pend = []
            continue
        if m in ("mov", "movzx", "movsx", "lea", "add", "sub", "inc", "dec",
                 "and", "or", "cmp", "test", "xor", "jmp", "je", "jne",
                 "jae", "jb", "jge", "jl", "jle", "jg", "call"):
            if m == "call":
                pend = []
            continue


if __name__ == "__main__":
    main()
